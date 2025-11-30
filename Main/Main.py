import streamlit as st
import google.generativeai as genai
import pandas as pd
import os
import json
import time
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ==========================================
# 1. 기본 설정 및 구글 시트 연결
# ==========================================
st.set_page_config(page_title="Job-Fit AI 도구 추천", page_icon="🤖", layout="wide")

try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    gcp_credentials = dict(st.secrets["gcp_service_account"])
except:
    st.error("Secrets 설정이 필요합니다.")
    st.stop()

genai.configure(api_key=GOOGLE_API_KEY)

# [중요] 본인의 구글 시트 주소
SHEET_URL = "https://docs.google.com/spreadsheets/d/176EoAIiDYnDiD9hORKABr_juIgRZZss5ApTqdaRCx5E/edit?gid=0#gid=0" 

# 구글 시트 클라이언트 연결 (시트 객체가 아니라 클라이언트 자체를 반환)
@st.cache_resource
def connect_to_client():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(gcp_credentials, scope)
    client = gspread.authorize(creds)
    return client

# [1번 시트] DB용 데이터 로드
def init_data():
    if "master_df" not in st.session_state:
        try:
            client = connect_to_client()
            worksheet = client.open_by_url(SHEET_URL).get_worksheet(0) # 첫 번째 시트
            data = worksheet.get_all_records()
            
            if data:
                df = pd.DataFrame(data)
            else:
                df = pd.DataFrame(columns=['직무','상황','결과물','추천도구','특징_및_팁','유료여부','링크','비추천수'])
            
            if '비추천수' not in df.columns: df['비추천수'] = 0
            df['비추천수'] = pd.to_numeric(df['비추천수'], errors='coerce').fillna(0).astype(int)
            
            st.session_state.master_df = df
        except Exception as e:
            st.error(f"데이터 로드 실패: {e}")
            st.session_state.master_df = pd.DataFrame(columns=['직무','상황','결과물','추천도구','특징_및_팁','유료여부','링크','비추천수'])

init_data()
df_tools = st.session_state.master_df

# [새 기능] 대화 내용을 2번 시트에 저장하는 함수
def save_log(job, situation, question, answer):
    try:
        client = connect_to_client()
        # 두 번째 시트 가져오기 (인덱스는 0부터 시작하므로 1이 두 번째)
        worksheet = client.open_by_url(SHEET_URL).get_worksheet(1) 
        
        if worksheet:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # [일시, 직무, 상황, 질문, 답변] 순서로 저장
            worksheet.append_row([now, job, situation, question, answer])
    except Exception as e:
        print(f"로그 저장 실패: {e}") # 사용자에게 에러를 띄우진 않음 (조용히 실패)

# ==========================================
# 2. 로직 함수들
# ==========================================
def parse_tools_from_text(user_text, ai_text):
    try:
        extractor_model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
        아래 대화에서 추천된 AI 도구 정보를 JSON 리스트로 추출해.
        Q: {user_text} / A: {ai_text}
        형식: [{{"추천도구": "이름", "직무": "...", "상황": "...", "결과물": "...", "특징_및_팁": "...", "유료여부": "...", "링크": "..."}}]
        """
        res = extractor_model.generate_content(prompt)
        text = res.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text) if text.startswith("[") else [json.loads(text)]
    except:
        return []

def update_data_single_tool(action_type, tool_data):
    df = st.session_state.master_df
    target = tool_data.get('추천도구')
    if not target: return False, "오류: 도구명 없음"

    try:
        # 동시성 해결을 위해 최신 데이터 다시 로드 시도
        try:
            client = connect_to_client()
            ws = client.open_by_url(SHEET_URL).get_worksheet(0)
            data = ws.get_all_records()
            if data:
                df = pd.DataFrame(data)
                if '비추천수' not in df.columns: df['비추천수'] = 0
                df['비추천수'] = pd.to_numeric(df['비추천수'], errors='coerce').fillna(0).astype(int)
        except:
            pass # 실패하면 메모리 데이터 사용

        msg, success, updated = "", True, False
        
        if action_type == 'like':
            if target in df['추천도구'].values:
                idx = df[df['추천도구'] == target].index[0]
                val = int(df.loc[idx, '비추천수'])
                if val > 0:
                    df.loc[idx, '비추천수'] = val - 1
                    msg, updated = f"✅ '{target}' 비추천 차감 완료!", True
                else:
                    msg = f"✨ '{target}'은(는) 이미 안전하게 저장됨."
            else:
                tool_data['비추천수'] = 0
                df = pd.concat([df, pd.DataFrame([tool_data])], ignore_index=True)
                msg, updated = f"🎉 '{target}' 시트에 저장 완료!", True
        
        elif action_type == 'dislike':
            if target not in df['추천도구'].values:
                return False, f"❓ '{target}'(미저장 도구)"
            else:
                idx = df[df['추천도구'] == target].index[0]
                val = int(df.loc[idx, '비추천수']) + 1
                df.loc[idx, '비추천수'] = val
                
                if val >= 3:
                    df = df.drop(idx).reset_index(drop=True)
                    msg = f"🗑️ '{target}' 삭제됨 (비추 3회)"
                else:
                    msg = f"📉 '{target}' 비추천 ({val}/3)"
                updated = True

        if updated:
            st.session_state.master_df = df
            try:
                ws.clear()
                ws.update([df.columns.values.tolist()] + df.values.tolist())
            except Exception as e:
                return False, f"시트 저장 실패: {e}"

        return success, msg
    except Exception as e:
        return False, str(e)

def reset_conversation():
    st.session_state.messages = []
    st.session_state.sb_job = "직접 입력"
    st.session_state.sb_situation = "직접 입력"
    st.session_state.sb_output = []
    for k in list(st.session_state.keys()):
        if k.startswith("tools_"): del st.session_state[k]

# ==========================================
# 3. UI 구성
# ==========================================
with st.sidebar:
    st.title("🎛️ 메뉴")

    st.divider()
    
    if "sb_job" not in st.session_state: st.session_state.sb_job = "직접 입력"
    if "sb_situation" not in st.session_state: st.session_state.sb_situation = "직접 입력"
    if "sb_output" not in st.session_state: st.session_state.sb_output = []

    selected_job = "직접 입력"
    selected_situation = "직접 입력"

    if not df_tools.empty:
        st.success(f"✅ DB 연동됨 ({len(df_tools)}개)")
        jobs = sorted(df_tools['직무'].astype(str).unique().tolist())
        selected_job = st.selectbox("직무", ["직접 입력"] + jobs, key="sb_job")
        if selected_job != "직접 입력":
            sits = sorted(df_tools[df_tools['직무'] == selected_job]['상황'].astype(str).unique().tolist())
            selected_situation = st.selectbox("상황", ["직접 입력"] + sits, key="sb_situation")
    else:
        st.error("데이터 로드 실패")
    
    output_format = st.multiselect("결과물 양식", ["보고서", "PPT", "이미지", "영상", "엑셀", "코드"], key="sb_output")

    st.divider()

    st.button("🔄 대화 초기화", on_click=reset_conversation, use_container_width=True)


# 메인 화면
st.title("🚀 Job-Fit AI 네비게이터")

welcome_msg = """
👋 **반가워요! 당신의 스마트한 업무 파트너, Job-Fit AI입니다.**

"이럴 땐 어떤 AI를 써야 하지?" 더 이상 혼자 고민하지 마세요.
상황을 말씀해 주시면 제가 딱 맞는 도구를 찾아드릴게요. 

💁‍♀️ **사용 꿀팁!**
1. **👈 왼쪽 사이드바**에서 직무를 선택하면 버튼 하나로 편하게 질문할 수 있어요.
2. 혹은 아래 채팅창에 **친구에게 묻듯 구체적으로** 물어보세요.
   * "마케터인데 무료로 쓸 수 있는 이미지 생성 툴 있어?"
   * "회의록 정리가 너무 귀찮은데 도와줄 AI 추천해 줘!"

마음에 드는 추천에는 **추천(👍)**을 눌러주시면 제가 꼭 기억해 둘게요!
반대로 추천이 마음에 들지 않으셨다면 **비추(👎)**를 눌러주세요.

📢 **안내사항**
* 더 나은 추천을 위해 **입력하신 직무와 상황, 그리고 피드백(👍/👎) 정보는 익명으로 저장**되어 학습에 활용됩니다.
* 질문에 **이름, 전화번호 등 개인정보**를 포함하지 않도록 주의해 주세요.

(도움이 되셨다면 [GitHub](https://github.com/Timber-Kim/Job-Fit-AI-Navigator)에서 **Star(⭐)**도 부탁드려요!)
"""
st.markdown(welcome_msg)

if "messages" not in st.session_state: st.session_state.messages = []

for i, m in enumerate(st.session_state.messages):
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m["role"] == "assistant":
            t_key = f"tools_{i}"
            if t_key not in st.session_state:
                if st.button("🛠️ 도구 관리", key=f"anlz_{i}"):
                    with st.spinner("분석 중..."):
                        u_q = st.session_state.messages[i-1]["content"] if i>0 else ""
                        found = parse_tools_from_text(u_q, m["content"])
                        if found:
                            st.session_state[t_key] = found
                            st.rerun()
                        else: st.error("도구 없음")
            else:
                tools = st.session_state[t_key]
                st.caption(f"💡 {len(tools)}개 도구 발견")
                for t in tools:
                    c1, c2, c3 = st.columns([3, 1, 1])
                    with c1: st.markdown(f"**🔧 {t['추천도구']}**")
                    with c2:
                        if st.button("👍", key=f"s_{i}_{t['추천도구']}"):
                            suc, msg = update_data_single_tool('like', t)
                            if suc: st.toast(msg, icon="✅"); time.sleep(1.5); st.rerun()
                            else: st.toast(msg, icon="⚠️"); time.sleep(1.5); st.rerun()
                    with c3:
                        if st.button("👎", key=f"d_{i}_{t['추천도구']}"):
                            suc, msg = update_data_single_tool('dislike', t)
                            if suc: st.toast(msg, icon="📉"); time.sleep(1.5); st.rerun()
                            else: 
                                if msg!="SILENT": st.toast(msg, icon="⚠️"); time.sleep(1.5); st.rerun()

def quick_ask(job, sit, out):
    outs = ", ".join(out) if out else ""
    q = f"직무: {job}, 상황: {sit}, 필요결과물: {outs}. 적합한 AI 도구 추천해줘."
    st.session_state.messages.append({"role": "user", "content": q})
    # [로그 저장을 위해 상태 저장]
    st.session_state.last_job = job
    st.session_state.last_sit = sit
    
    st.session_state.sb_job = "직접 입력"
    st.session_state.sb_situation = "직접 입력"
    st.session_state.sb_output = []

if selected_job != "직접 입력" and selected_situation != "직접 입력":
    st.button(f"🔍 '{selected_job}' - '{selected_situation}' 추천받기", type="primary", on_click=quick_ask, args=(selected_job, selected_situation, output_format), use_container_width=True)

if prompt := st.chat_input("직접 질문하기(예시. 나는 사실 치킨집 사장인데 개발자가 되고싶어 프론트엔드 개발자가 되고싶은데 판교어를 배우고 싶어 판교어를 가르쳐주는 AI 없을까?))"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    # 직접 질문 시 직무/상황은 '직접 입력' 또는 '알 수 없음' 처리
    st.session_state.last_job = "직접 입력" 
    st.session_state.last_sit = "직접 입력"
    st.rerun()

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        ph = st.empty()
        with st.spinner("생각 중..."):
            try:
                hist = [{"role": "user" if m["role"]=="user" else "model", "parts": [m["content"]]} for m in st.session_state.messages[:-1]]
                
                csv_txt = ""
                if not df_tools.empty:
                    cols = [c for c in df_tools.columns if c!='비추천수']
                    csv_txt = df_tools[cols].to_string(index=False)
                
                sys_prompt = f"""
                너는 AI 도구 큐레이터야. 사용자 상황에 맞는 도구를 추천해.
                [DB 도구 목록]
                {csv_txt}
                전략: DB와 새로운 도구를 섞어서(하이브리드) 추천.
                형식: 도구명, 이유, 가격, 링크, 꿀팁 포함.
                """
                model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=sys_prompt)
                
                chat = model.start_chat(history=hist)
                resp = chat.send_message(st.session_state.messages[-1]["content"])
                ph.markdown(resp.text)
                st.session_state.messages.append({"role": "assistant", "content": resp.text})
                
                # [로그 저장 실행]
                job_log = st.session_state.get("last_job", "직접 입력")
                sit_log = st.session_state.get("last_sit", "직접 입력")
                save_log(job_log, sit_log, st.session_state.messages[-2]["content"], resp.text)
                
                st.rerun()
            except Exception as e:
                ph.error(f"오류: {e}")
                st.session_state.messages.pop()