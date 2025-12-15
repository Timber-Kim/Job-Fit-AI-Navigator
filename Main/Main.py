import streamlit as st
import time
from modules.config import WELCOME_MSG
from modules.db_manager import load_db, update_db, save_log
from modules.ai_manager import get_ai_response, parse_tools
from google.api_core import exceptions

st.set_page_config(page_title="Job-Fit AI 네비게이터", page_icon="🤖", layout="wide")

# 1. 세션 초기화
if "messages" not in st.session_state: st.session_state.messages = []
if "master_df" not in st.session_state: st.session_state.master_df = load_db()

df_tools = st.session_state.master_df

# ==========================================
# 429 오류 처리 (st.status 사용)
# ==========================================
def get_ai_response_safe(messages, df):
    """
    AI 응답을 요청하되, 429 오류가 발생하면 
    상태바(Spinner) 안에서 대기 과정을 보여줍니다.
    """
    max_retries = 3
    wait_time = 30  # 30초 대기

    # st.status를 사용하여 로딩 과정을 깔끔하게 묶기
    with st.status("AI가 답변을 생성하고 있습니다...", expanded=False) as status:
        
        for attempt in range(max_retries):
            try:
                # 1. 답변 생성 시도
                response = get_ai_response(messages, df)
                
                # 성공하면 상태 업데이트 후 반환
                status.update(label="✅ 답변 생성 완료!", state="complete", expanded=False)
                return response
                
            except exceptions.ResourceExhausted:
                # 2. 429 오류 발생 시 (이 부분이 핵심!)
                msg = f"⏳ 사용량이 많아 잠시 쉬고 있습니다... ({attempt + 1}/{max_retries})"
                status.update(label=msg, state="running") # 상태바 메시지 변경
            
                for _ in range(wait_time):
                    time.sleep(1)
                
            except Exception as e:
                # 그 외 오류
                status.update(label="❌ 오류 발생", state="error")
                return f"❌ 오류가 발생했습니다: {str(e)}"

    return "❌ 재시도 횟수를 초과했습니다. 잠시 후 다시 질문해 주세요."

# [핵심] AI가 답변 생성 중인지 확인
is_generating = False
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    is_generating = True

# ==========================================
# 2. 사이드바 (수정된 전체 코드)
# ==========================================

# [함수 1] 조건만 초기화하는 함수
def reset_conditions():
    st.session_state.sb_job = "직접 입력"
    st.session_state.sb_situation = "직접 입력"
    st.session_state.sb_output = []

# [함수 2] 대화 내용까지 싹 다 초기화하는 함수
def reset_all():
    # 1. 대화 내용 삭제
    st.session_state.messages = []
    
    # 2. 조건 초기화 (위의 함수 재활용)
    reset_conditions()
    
    # 3. 도구 관련 데이터 삭제
    for k in list(st.session_state.keys()):
        if k.startswith("tools_"): del st.session_state[k]

with st.sidebar:
    st.title("🎛️ 메뉴")

    st.divider()
    
with st.sidebar:
   # 4. 사용자 API 키 입력창
    user_api_key_input = st.text_input(
        "🔑 (선택) 내 API Key 사용", 
        value=st.session_state.get("USER_API_KEY", ""), # 기존 값 표시
        type= "password", 
        help= "Google AI Studio에서 발급받은 키를 입력하면 더 빠르고 안정적입니다. 키는 저장되지 않습니다.",
        disabled=is_generating
    )
    
    # 입력 값이 바뀌었을 때
    if "user_api_key_input" not in st.session_state:
        st.session_state["user_api_key_input"] = ""

    if user_api_key_input != st.session_state["user_api_key_input"]:
        st.session_state["user_api_key_input"] = user_api_key_input
        
        # 입력된 키를 세션 상태에 저장 (빈 칸이면 키 삭제)
        if user_api_key_input.strip():
            st.session_state["USER_API_KEY"] = user_api_key_input.strip()
        else:
            if "USER_API_KEY" in st.session_state:
                del st.session_state["USER_API_KEY"]
            
        # 키 변경 후 바로 반영을 위해 reran
        st.rerun()
        
    st.divider()

    # 1) 세션 상태 초기화
    if "sb_job" not in st.session_state: st.session_state.sb_job = "직접 입력"
    if "sb_situation" not in st.session_state: st.session_state.sb_situation = "직접 입력"
    if "sb_output" not in st.session_state: st.session_state.sb_output = []

    # 2) DB 연결 상태 표시
    if not df_tools.empty:
        st.success("✅ DB 연결 완료")
    else:
        st.error("DB 연결 실패")
    


    # 3) 직무 선택창
    if not df_tools.empty:
        current_jobs = sorted(df_tools['직무'].astype(str).unique().tolist())
        current_jobs = [j for j in current_jobs if j != "직접 입력"]
        job_options = ["직접 입력"] + current_jobs
    else:
        job_options = ["직접 입력"]
        
    selected_job = st.selectbox("직무", job_options, key="sb_job", disabled=is_generating)
    
    # 4) 상황 선택창
    selected_situation = "직접 입력"
    if selected_job != "직접 입력":
        sits = sorted(df_tools[df_tools['직무'] == selected_job]['상황'].astype(str).unique().tolist())
        selected_situation = st.selectbox("상황", ["직접 입력"] + sits, key="sb_situation", disabled=is_generating)

    # 5) 결과물 양식 선택
    output_format = st.multiselect("결과물 양식", ["보고서", "PPT", "이미지", "영상", "엑셀", "코드"], key="sb_output", disabled=is_generating)

    # GitHub 홍보
    st.markdown("---") 
    GITHUB_URL = "https://github.com/Timber-Kim/Job-Fit-AI-Navigator" 

    st.info(
        "**🌟 프로젝트가 마음에 드시나요?**\n\n"
        "이슈 제보나 피드백, 응원은 언제나 환영합니다! "
        f"[GitHub 바로가기]({GITHUB_URL})"
    )  
    st.divider()
    
# 6) 버튼 영역
    col1, col2 = st.columns(2)
    
    with col1:
        st.button("🔄 조건 초기화", 
                  use_container_width=True, 
                  disabled=is_generating,
                  on_click=reset_conditions) 
            
    with col2:
        st.button("🗑️ 대화 삭제", 
                  use_container_width=True, 
                  disabled=is_generating, 
                  on_click=reset_all)



# ==========================================
# 3. 메인 화면 & 대화 내역
# ==========================================
st.title("🚀 Job-Fit AI 네비게이터")
st.markdown(WELCOME_MSG)


for i, m in enumerate(st.session_state.messages):
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        
        if m["role"] == "assistant":
            t_key = f"tools_{i}"
            if t_key not in st.session_state:
                if st.button("🛠️ 도구 저장/피드백", key=f"btn_{i}", disabled=is_generating):
                    with st.status("답변을 분석하고 도구를 추출하고 있습니다...", expanded=False) as status:
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
                        if st.button("👍", key=f"like_{i}_{t['추천도구']}", disabled=is_generating):
                            suc, msg, new_df = update_db('like', t, st.session_state.master_df)
                            if suc:
                                st.session_state.master_df = new_df
                                st.toast(msg, icon="✅")
                                time.sleep(1.5)
                            st.rerun()
                    with c3:
                        if st.button("👎", key=f"dislike_{i}_{t['추천도구']}", disabled=is_generating):
                            suc, msg, new_df = update_db('dislike', t, st.session_state.master_df)
                            if suc and msg != "SILENT":
                                st.session_state.master_df = new_df
                                st.toast(msg, icon="📉")
                                time.sleep(1.5)
                            st.rerun()

# ==========================================
# 4. 빠른 추천 버튼 & 질문 처리
# ==========================================
def quick_ask(job, sit, out):
    outs_msg = f" (필요한 결과물: {', '.join(out)})" if out else ""
    q = f"나 **{job}**인데, **{sit}** 업무 할 때 도움되는 AI 도구 좀 추천해 줘.{outs_msg}"
    st.session_state.messages.append({"role": "user", "content": q})
    st.session_state.sb_job = "직접 입력"
    st.session_state.sb_situation = "직접 입력"
    st.session_state.sb_output = []

if selected_job != "직접 입력" and selected_situation != "직접 입력":
    st.button(f"🔍 '{selected_job}' - '{selected_situation}' 추천받기", 
              type="primary", 
              on_click=quick_ask, 
              args=(selected_job, selected_situation, output_format), 
              use_container_width=True,
              disabled=is_generating)

def ask_ai_direct(prompt_text):
    st.session_state.messages.append({"role": "user", "content": prompt_text})
    st.rerun()

if prompt := st.chat_input("어떤 업무 때문에 고민이신가요?(예시 : 초보 개발자를 위한 AI 도구를 추천해줘.)", disabled=is_generating):
    ask_ai_direct(prompt)

# ==========================================
# 5. AI 응답 생성
# ==========================================
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        ph = st.empty()
        
        # 함수 호출
        response_text = get_ai_response_safe(st.session_state.messages, st.session_state.master_df)
        
        ph.markdown(response_text)
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        
        if not response_text.startswith("❌"):
            log_job = selected_job if selected_job != "직접 입력" else "직접/기타"
            log_sit = selected_situation if selected_situation != "직접 입력" else "직접/기타"
            save_log(log_job, log_sit, st.session_state.messages[-2]["content"], response_text) 
        st.rerun()