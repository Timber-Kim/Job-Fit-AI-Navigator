import streamlit as st
import time
from modules.config import WELCOME_MSG
from modules.db_manager import load_db, update_db, save_log, clean_job_titles
from modules.ai_manager import get_ai_response, parse_tools

st.set_page_config(page_title="Job-Fit AI 네비게이터", page_icon="🤖", layout="wide")

if "messages" not in st.session_state: st.session_state.messages = []
if "master_df" not in st.session_state: st.session_state.master_df = load_db()

df_tools = st.session_state.master_df

# ==========================================
# 1. 사이드바
# ==========================================
with st.sidebar:
    st.title("🎛️ 메뉴")
    st.divider()
    
    if "sb_job" not in st.session_state: st.session_state.sb_job = "직접 입력"
    if "sb_situation" not in st.session_state: st.session_state.sb_situation = "직접 입력"
    if "sb_output" not in st.session_state: st.session_state.sb_output = []

    if not df_tools.empty:
        st.success("✅ DB 연결 완료")
    else:
        st.error("DB 연결 실패")

    if not df_tools.empty:
        current_jobs = sorted(df_tools['직무'].astype(str).unique().tolist())
        current_jobs = [j for j in current_jobs if j != "직접 입력"]
        job_options = ["직접 입력"] + current_jobs
    else:
        job_options = ["직접 입력"]
        
    selected_job = st.selectbox("직무", job_options, key="sb_job")
    
    selected_situation = "직접 입력"
    if selected_job != "직접 입력":
        sits = sorted(df_tools[df_tools['직무'] == selected_job]['상황'].astype(str).unique().tolist())
        selected_situation = st.selectbox("상황", ["직접 입력"] + sits, key="sb_situation")

    output_format = st.multiselect("결과물 양식", ["보고서", "PPT", "이미지", "영상", "엑셀", "코드"], key="sb_output")

    st.divider()
    if st.button("🔄 새로운 대화 시작", use_container_width=True):
        st.session_state.messages = []
        st.session_state.sb_job = "직접 입력"
        st.session_state.sb_situation = "직접 입력"
        st.session_state.sb_output = []
        for k in list(st.session_state.keys()):
            if k.startswith("tools_"): del st.session_state[k]
        st.rerun()

# ==========================================
# 2. 메인 화면 & 대화 내역
# ==========================================
st.title("🚀 Job-Fit AI 네비게이터")
st.markdown(WELCOME_MSG)

for i, m in enumerate(st.session_state.messages):
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        
        if m["role"] == "assistant":
            t_key = f"tools_{i}"
            if t_key not in st.session_state:
                if st.button("🛠️ 도구 저장/피드백", key=f"btn_{i}"):
                    with st.spinner("답변 분석 중..."):
                        u_q = st.session_state.messages[i-1]["content"] if i>0 else ""
                        found = parse_tools(u_q, m["content"])
                        if found:
                            st.session_state[t_key] = found
                            st.rerun()
                        else: st.warning("추출된 도구가 없습니다.")
            else:
                tools = st.session_state[t_key]
                st.caption(f"💡 {len(tools)}개의 도구 확인됨")
                for t in tools:
                    c1, c2, c3 = st.columns([4, 1, 1])
                    with c1: st.markdown(f"**🔧 {t['추천도구']}**")
                    with c2:
                        if st.button("👍", key=f"like_{i}_{t['추천도구']}"):
                            suc, msg, new_df = update_db('like', t, st.session_state.master_df)
                            if suc:
                                st.session_state.master_df = new_df
                                st.toast(msg, icon="✅")
                                time.sleep(1.5)
                            st.rerun()
                    with c3:
                        if st.button("👎", key=f"dislike_{i}_{t['추천도구']}"):
                            suc, msg, new_df = update_db('dislike', t, st.session_state.master_df)
                            if suc and msg != "SILENT":
                                st.session_state.master_df = new_df
                                st.toast(msg, icon="📉")
                                time.sleep(1.5)
                            st.rerun()

# ==========================================
# 3. 빠른 추천 버튼 (대화 내역 아래)
# ==========================================
def quick_ask(job, sit, out):
    outs = ", ".join(out) if out else ""
    q = f"직무: {job}, 상황: {sit}, 필요결과물: {outs}. 적합한 AI 도구 추천해줘."
    st.session_state.messages.append({"role": "user", "content": q})
    
    # 선택값 초기화 (이게 있어야 버튼이 사라짐)
    st.session_state.sb_job = "직접 입력"
    st.session_state.sb_situation = "직접 입력"
    st.session_state.sb_output = []
    
    # [수정됨] st.rerun() 제거! 
    # on_click 콜백이 끝나면 Streamlit이 자동으로 rerun하므로 없어도 됩니다.

if selected_job != "직접 입력" and selected_situation != "직접 입력":
    st.button(f"🔍 '{selected_job}' - '{selected_situation}' 추천받기", 
              type="primary", 
              on_click=quick_ask, 
              args=(selected_job, selected_situation, output_format), 
              use_container_width=True)

# ==========================================
# 4. 입력 및 AI 응답
# ==========================================
def ask_ai_direct(prompt_text):
    st.session_state.messages.append({"role": "user", "content": prompt_text})
    st.rerun()

if prompt := st.chat_input("어떤 업무 때문에 고민이신가요? (예: 마케팅용 이미지 생성, 회의록 정리)"):
    ask_ai_direct(prompt)

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        ph = st.empty()
        with st.spinner("AI가 대화내용을 분석 중입니다..."):
            response_text = get_ai_response(st.session_state.messages, st.session_state.master_df)
            ph.markdown(response_text)
            st.session_state.messages.append({"role": "assistant", "content": response_text})
            
            log_job = selected_job if selected_job != "직접 입력" else "직접/기타"
            log_sit = selected_situation if selected_situation != "직접 입력" else "직접/기타"
            save_log(log_job, log_sit, st.session_state.messages[-2]["content"], response_text)
            st.rerun()