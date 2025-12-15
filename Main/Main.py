import streamlit as st
import time
from modules.config import WELCOME_MSG
from modules.db_manager import load_db, update_db, save_log, clean_job_titles
from modules.ai_manager import get_ai_response, parse_tools
from google.api_core import exceptions

st.set_page_config(page_title="Job-Fit AI 네비게이터", page_icon="🤖", layout="wide")

# 1. 세션 초기화
if "messages" not in st.session_state: st.session_state.messages = []
if "master_df" not in st.session_state: st.session_state.master_df = load_db()

df_tools = st.session_state.master_df

# ==========================================
# ✅ [추가됨] 429 오류(사용량 초과) 자동 해결 함수
# ==========================================
def get_ai_response_safe(messages, df):
    """
    AI 응답을 요청하되, 429 오류(Quota Exceeded)가 발생하면 
    자동으로 대기했다가 재시도합니다.
    """
    max_retries = 3
    wait_time = 30  # 30초 대기

    for attempt in range(max_retries):
        try:
            # 원래 함수 호출
            return get_ai_response(messages, df)
            
        except exceptions.ResourceExhausted:
            # 429 오류 발생 시 화면 알림 및 대기
            msg = f"⚠️ 무료 사용량이 초과되었습니다. {wait_time}초 대기 후 재시도합니다... ({attempt + 1}/{max_retries})"
            st.warning(msg)
            st.toast(msg, icon="⏳")
            
            time.sleep(wait_time) # 프로그램 잠시 멈춤 (대기)
            
        except Exception as e:
            # 그 외 오류는 즉시 반환
            return f"❌ 오류가 발생했습니다: {str(e)}"

    return "❌ 재시도 횟수를 초과했습니다. 잠시 후 다시 질문해 주세요."

# [핵심] AI가 답변 생성 중인지 확인 (생성 중이면 입력을 막기 위함)
is_generating = False
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    is_generating = True

# ==========================================
# 2. 사이드바 (AI 생각 중일 때 비활성화 처리)
# ==========================================
with st.sidebar:
    st.title("🎛️ 메뉴")
    st.divider()
    
    # 세션 상태 키 초기화
    if "sb_job" not in st.session_state: st.session_state.sb_job = "직접 입력"
    if "sb_situation" not in st.session_state: st.session_state.sb_situation = "직접 입력"
    if "sb_output" not in st.session_state: st.session_state.sb_output = []

    if not df_tools.empty:
        st.success("✅ DB 연결 완료")
    else:
        st.error("DB 연결 실패")

    # 직무 리스트 준비
    if not df_tools.empty:
        current_jobs = sorted(df_tools['직무'].astype(str).unique().tolist())
        current_jobs = [j for j in current_jobs if j != "직접 입력"]
        job_options = ["직접 입력"] + current_jobs
    else:
        job_options = ["직접 입력"]
        
    # [핵심] disabled=is_generating 적용 (AI가 생각 중이면 선택 불가)
    selected_job = st.selectbox(
        "직무", job_options, 
        key="sb_job", 
        disabled=is_generating
    )
    
    selected_situation = "직접 입력"
    if selected_job != "직접 입력":
        sits = sorted(df_tools[df_tools['직무'] == selected_job]['상황'].astype(str).unique().tolist())
        selected_situation = st.selectbox(
            "상황", ["직접 입력"] + sits, 
            key="sb_situation",
            disabled=is_generating
        )

    output_format = st.multiselect(
        "결과물 양식", ["보고서", "PPT", "이미지", "영상", "엑셀", "코드"], 
        key="sb_output",
        disabled=is_generating
    )

    st.divider()
    
    # 초기화 버튼도 생각 중엔 비활성화
    if st.button("🔄 새로운 대화 시작", use_container_width=True, disabled=is_generating):
        st.session_state.messages = []
        st.session_state.sb_job = "직접 입력"
        st.session_state.sb_situation = "직접 입력"
        st.session_state.sb_output = []
        for k in list(st.session_state.keys()):
            if k.startswith("tools_"): del st.session_state[k]
        st.rerun()

# ==========================================
# 3. 메인 화면 & 대화 내역
# ==========================================
st.title("🚀 Job-Fit AI 네비게이터")
st.markdown(WELCOME_MSG)

for i, m in enumerate(st.session_state.messages):
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        
        # AI 답변 아래 도구 관리 UI
        if m["role"] == "assistant":
            t_key = f"tools_{i}"
            if t_key not in st.session_state:
                # 분석 버튼도 생성 중엔 비활성화 (꼬임 방지)
                if st.button("🛠️ 도구 저장/피드백", key=f"btn_{i}", disabled=is_generating):
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
    # 결과물 조건이 있을 때만 문장 뒤에 자연스럽게 붙임
    outs_msg = f" (필요한 결과물: {', '.join(out)})" if out else ""
    
    # "나 OOO인데, OOO 할 때 쓸만한 거 추천해줘" 스타일
    q = f"나 **{job}**인데, **{sit}** 업무 할 때 도움되는 AI 도구 좀 추천해 줘.{outs_msg}"
    
    st.session_state.messages.append({"role": "user", "content": q})
    
    # 선택값 초기화 (버튼 사라지게)
    st.session_state.sb_job = "직접 입력"
    st.session_state.sb_situation = "직접 입력"
    st.session_state.sb_output = []

# 조건이 맞을 때만 버튼 표시 (생성 중일 때는 버튼도 숨김 or 비활성화)
if selected_job != "직접 입력" and selected_situation != "직접 입력":
    st.button(f"🔍 '{selected_job}' - '{selected_situation}' 추천받기", 
              type="primary", 
              on_click=quick_ask, 
              args=(selected_job, selected_situation, output_format), 
              use_container_width=True,
              disabled=is_generating) # 여기서도 막아둠

# 직접 질문 입력 (생성 중엔 숨김 or 비활성화)
def ask_ai_direct(prompt_text):
    st.session_state.messages.append({"role": "user", "content": prompt_text})
    st.rerun()

if prompt := st.chat_input("어떤 업무 때문에 고민이신가요? (예: 마케팅용 이미지 생성, 회의록 정리)", disabled=is_generating):
    ask_ai_direct(prompt)

# ==========================================
# 5. AI 응답 생성
# ==========================================
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        ph = st.empty()
        with st.spinner("AI가 대화내용을 분석 중입니다..."):
            response_text = get_ai_response(st.session_state.messages, st.session_state.master_df)
            ph.markdown(response_text)
            st.session_state.messages.append({"role": "assistant", "content": response_text})
            
            # 로그 저장 (직접 입력인 경우 처리)
            log_job = selected_job if selected_job != "직접 입력" else "직접/기타"
            log_sit = selected_situation if selected_situation != "직접 입력" else "직접/기타"
            save_log(log_job, log_sit, st.session_state.messages[-2]["content"], response_text)
            
            # 답변 완료 후 UI 잠금 해제를 위해 리런
            st.rerun()