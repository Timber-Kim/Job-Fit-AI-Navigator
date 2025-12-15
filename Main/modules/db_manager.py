import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
from .config import SHEET_URL
# [중요] AI 매니저에서 표준화 함수 가져오기
from .ai_manager import normalize_job_category

# 구글 시트 연결
@st.cache_resource
def connect_to_client():
    try:
        gcp_credentials = dict(st.secrets["gcp_service_account"])
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(gcp_credentials, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"구글 시트 연결 오류: {e}")
        return None

# 데이터 로드
def load_db():
    client = connect_to_client()
    if not client: return pd.DataFrame()

    try:
        ws = client.open_by_url(SHEET_URL).get_worksheet(0)
        data = ws.get_all_records()
        
        if data:
            df = pd.DataFrame(data)
        else:
            df = pd.DataFrame(columns=['직무','상황','결과물','추천도구','특징_및_팁','유료여부','링크','비추천수','추천수'])
        
        for col in ['비추천수', '추천수']:
            if col not in df.columns: df[col] = 0
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
        return df
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return pd.DataFrame()

# 로그 저장
def save_log(job, situation, question, answer):
    try:
        client = connect_to_client()
        ws = client.open_by_url(SHEET_URL).get_worksheet(1)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ws.append_row([now, job, situation, question, answer])
    except:
        pass 

# DB 업데이트 (자동 직무 표준화 적용)
def update_db(action_type, tool_data, current_df):
    target = tool_data.get('추천도구')

    if not target: return False, "오류", current_df

    try:
        client = connect_to_client()
        ws = client.open_by_url(SHEET_URL).get_worksheet(0)
        
        # 1. 최신 데이터 가져오기 (충돌 방지)
        data = ws.get_all_records()
        df = pd.DataFrame(data) if data else current_df.copy()
        
        # 2. 숫자형 컬럼 안전 처리
        for col in ['비추천수', '추천수']:
            if col not in df.columns: df[col] = 0
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

        msg = ""
        updated = False

        # --- 로직 처리 (좋아요/싫어요) ---
        if action_type == 'like':
            if target in df['추천도구'].values:
                idx = df[df['추천도구'] == target].index[0]
                df.loc[idx, '추천수'] += 1
                val_dislike = int(df.loc[idx, '비추천수'])
                if val_dislike > 0: df.loc[idx, '비추천수'] = val_dislike - 1
                msg = f"✨ '{target}'를 추천했습니다!"
            else:
                # [신규 추가 로직]
                input_job = tool_data.get('직무', '기타')
                existing_jobs = [j for j in df['직무'].unique() if j != "직접 입력"]

                # 👇 여기서 이제 '상태바'가 뜨면서 안전하게 실행됩니다.
                standardized_job = normalize_job_category(input_job, existing_jobs)
                tool_data['직무'] = standardized_job

                # 필수값 초기화
                tool_data['비추천수'] = 0
                tool_data['추천수'] = 1
                
                # 데이터 합치기
                df = pd.concat([df, pd.DataFrame([tool_data])], ignore_index=True)
                msg = f"🎉 '{target}' 등록 완료! (직무: {standardized_job})"
            updated = True
        
        elif action_type == 'dislike':
            if target in df['추천도구'].values:
                idx = df[df['추천도구'] == target].index[0]
                val = int(df.loc[idx, '비추천수']) + 1
                if val >= 3:
                    df = df.drop(idx).reset_index(drop=True)
                else:
                    df.loc[idx, '비추천수'] = val
                msg = f"📉 의견이 반영되었습니다."
                updated = True
            else:
                return False, "SILENT", current_df

        # --- [핵심 수정 구간: 안전하게 저장하기] ---
        if updated:
            # 1. NaN(빈 값) 제거 (이게 없으면 JSON 에러남)
            df = df.fillna("") 
            
            # 2. 모든 데이터를 문자열로 변환 (가장 강력한 안전장치)
            # 숫자가 섞여있거나 Timestamp가 있으면 gspread가 에러를 낼 수 있음
            df_for_upload = df.astype(str)

            # 3. 업로드할 데이터를 리스트로 '미리' 변환
            # (여기서 에러가 나면 시트는 건드리지 않고 멈춤 -> 데이터 보존됨)
            payload = [df_for_upload.columns.values.tolist()] + df_for_upload.values.tolist()
            
            # 4. 데이터 준비가 완벽하게 끝난 후에 시트 초기화 및 업데이트
            ws.clear()
            ws.update(range_name='A1', values=payload) # 문법 호환성 개선
            
            return True, msg, df
        
        return True, msg, df

    except Exception as e:
        # 에러가 나도 기존 df를 반환해서 화면이 깨지지 않게 함
        print(f"Update DB Error: {e}") 
        return False, f"오류 발생: {e}", current_df

# 직무 리스트 반환 (Main.py 사이드바용)
def clean_job_titles():
    df = load_db()
    if df.empty: return []
    jobs = sorted(df['직무'].astype(str).str.strip().unique().tolist())
    return [j for j in jobs if j != "직접 입력"]