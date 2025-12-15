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
        
        data = ws.get_all_records()
        df = pd.DataFrame(data) if data else current_df.copy()
        
        for col in ['비추천수', '추천수']:
            if col not in df.columns: df[col] = 0
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

        msg = ""
        updated = False

        if action_type == 'like':
            if target in df['추천도구'].values:
                # 이미 존재 -> 추천수만 증가
                idx = df[df['추천도구'] == target].index[0]
                df.loc[idx, '추천수'] += 1
                
                val_dislike = int(df.loc[idx, '비추천수'])
                if val_dislike > 0: df.loc[idx, '비추천수'] = val_dislike - 1
                
                msg = f"✨ '{target}'를 추천했습니다!"
            else:
                # [핵심] 신규 저장 시 -> AI 자동 직무 표준화 실행!
                input_job = tool_data.get('직무', '기타')
                existing_jobs = [j for j in df['직무'].unique() if j != "직접 입력"]
                
                # AI에게 물어봐서 표준화된 직무명 받아오기
                standardized_job = normalize_job_category(input_job, existing_jobs)
                tool_data['직무'] = standardized_job  # 변경된 직무로 덮어쓰기

                tool_data['비추천수'] = 0
                tool_data['추천수'] = 1
                df = pd.concat([df, pd.DataFrame([tool_data])], ignore_index=True)
                
                msg = f"🎉 '{target}' 등록 완료! (직무: {standardized_job}로 분류됨)"
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

        if updated:
            ws.clear()
            ws.update([df.columns.values.tolist()] + df.values.tolist())
            return True, msg, df
        
        return True, msg, df

    except Exception as e:
        return False, f"오류: {e}", current_df

# 직무 리스트 반환 (Main.py 사이드바용)
def clean_job_titles():
    df = load_db()
    if df.empty: return []
    jobs = sorted(df['직무'].astype(str).str.strip().unique().tolist())
    return [j for j in jobs if j != "직접 입력"]