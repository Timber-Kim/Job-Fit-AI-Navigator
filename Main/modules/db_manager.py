import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
from .config import SHEET_URL
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

# DB 업데이트
def update_db(action_type, tool_data, current_df):
    target = tool_data.get('추천도구')
    if not target: return False, "오류", current_df

    try:
        client = connect_to_client()
        ws = client.open_by_url(SHEET_URL).get_worksheet(0)
        
        # 1. 최신 데이터 가져오기 (동시성 문제 최소화)
        data = ws.get_all_records()
        df = pd.DataFrame(data) if data else current_df.copy()
        
        # 2. 숫자형 컬럼 안전 처리 (빈 값은 0으로)
        for col in ['비추천수', '추천수']:
            if col not in df.columns: df[col] = 0
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

        msg = ""
        updated = False

        # --- [좋아요 👍] 로직 ---
        if action_type == 'like':
            if target in df['추천도구'].values:
                # 이미 있으면 점수 +1
                idx = df[df['추천도구'] == target].index[0]
                df.loc[idx, '추천수'] += 1
                msg = f"✨ '{target}' 추천수 증가! (현재: {df.loc[idx, '추천수']})"
            else:
                # 없으면 신규 등록 (기본 점수 1점)
                input_job = tool_data.get('직무', '기타')
                existing_jobs = [j for j in df['직무'].unique() if j != "직접 입력"]
                
                # 직무 표준화
                standardized_job = normalize_job_category(input_job, existing_jobs)
                tool_data['직무'] = standardized_job

                tool_data['비추천수'] = 0
                tool_data['추천수'] = 1  # 시작 점수
                
                df = pd.concat([df, pd.DataFrame([tool_data])], ignore_index=True)
                msg = f"🎉 '{target}' 등록 완료! (직무: {standardized_job})"
            updated = True
        
        # --- [싫어요 👎] 로직 ---
        elif action_type == 'dislike':
            if target in df['추천도구'].values:
                idx = df[df['추천도구'] == target].index[0]
                
                # 1. 추천수(점수) 1 감소
                current_score = int(df.loc[idx, '추천수']) - 1
                
                # 2. 점수가 -3 이하이면 삭제
                if current_score <= -3:
                    df = df.drop(idx).reset_index(drop=True)
                    msg = f"🗑️ 평가 점수 미달(-3)로 '{target}' 도구가 삭제되었습니다."
                else:
                    # 삭제 기준이 아니라면 점수만 업데이트
                    df.loc[idx, '추천수'] = current_score
                    msg = f"📉 추천 점수가 차감되었습니다. (현재: {current_score})"
                
                updated = True
            else:
                # DB에 없는 도구(AI가 방금 찾은 도구)에 비추천을 누른 경우
                # 아직 저장되지 않았으므로 아무 일도 일어나지 않음 (혹은 사용자에게 알림)
                return False, "SILENT", current_df

        # --- [데이터 저장] ---
        if updated:
            df = df.fillna("") 
            df_for_upload = df.astype(str) # 모든 값을 문자열로 변환
            
            payload = [df_for_upload.columns.values.tolist()] + df_for_upload.values.tolist()
            
            ws.clear()
            ws.update(range_name='A1', values=payload)
            
            return True, msg, df
        
        return True, msg, df

    except Exception as e:
        print(f"Update DB Error: {e}") 
        return False, f"오류 발생: {e}", current_df

# 직무 리스트 반환 (Main.py 사이드바용)
def clean_job_titles():
    df = load_db()
    if df.empty: return []
    jobs = sorted(df['직무'].astype(str).str.strip().unique().tolist())
    return [j for j in jobs if j != "직접 입력"]