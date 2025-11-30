import streamlit as st
import google.generativeai as genai
import pandas as pd
import os
import json

# ==========================================
# 1. 기본 설정 및 데이터 로드
# ==========================================
st.set_page_config(page_title="Job-Fit AI 도구 추천",
                   page_icon="🤖",
                   layout="wide")

try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    GOOGLE_API_KEY = "여기에_API_키를_입력하세요" 

genai.configure(api_key=GOOGLE_API_KEY)

# 절대 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
CSV_FILE_PATH = os.path.join(current_dir, 'ai_tools.csv')

# 데이터 로드 함수
@st.cache_data
def load_data():
    if not os.path.exists(CSV_FILE_PATH):
        return None

    try:
        df = pd.read_csv(CSV_FILE_PATH, encoding='utf-8-sig', on_bad_lines='skip')
    except:
        try:
            df = pd.read_csv(CSV_FILE_PATH, encoding='cp949', on_bad_lines='skip')
        except:
            return None

    if df is not None:
        if '비추천수' not in df.columns:
            df['비추천수'] = 0
            df.to_csv(CSV_FILE_PATH, index=False, encoding='utf-8-sig')
            
    return df

df_tools = load_data()

# ==========================================
# 2. AI 정보 추출 및 CSV 업데이트 로직
# ==========================================
def extract_and_update_csv(action_type, user_text, ai_text):
    try:
        extractor_model = genai.GenerativeModel('gemini-2.5-pro')
        
        extraction_prompt = f"""
        너는 데이터 추출기야. 아래 대화를 분석해서 정보를 JSON 리스트로 줘.
        
        [대화]
        Q: {user_text}
        A: {ai_text}
        
        [요청사항]
        1. AI 답변에서 추천한 **모든** 핵심 '추천도구'(이름)을 찾아줘.
        2. action이 'like'라면, 각 도구별로 직무, 상황, 결과물, 특징_및_팁, 유료여부, 링크 정보도 추출해.
        
        출력 포맷(JSON List):
        [
            {{
                "추천도구": "도구A",
                "직무": "...",
                "상황": "...",
                "결과물": "...",
                "특징_및_팁": "...",
                "유료여부": "...",
                "링크": "..."
            }}
        ]
        오직 JSON List만 출력해.
        """
        
        result = extractor_model.generate_content(extraction_prompt)
        cleaned_json = result.text.replace("```json", "").replace("```", "").strip()
        
        tools_data_list = json.loads(cleaned_json)
        if isinstance(tools_data_list, dict):
            tools_data_list = [tools_data_list]

        if os.path.exists(CSV_FILE_PATH):
            df = pd.read_csv(CSV_FILE_PATH, encoding='utf-8-sig', on_bad_lines='skip')
        else:
            return False, "CSV 파일이 없습니다."

        if '비추천수' not in df.columns:
            df['비추천수'] = 0

        result_messages = []
        has_change = False

        for data_dict in tools_data_list:
            target_tool = data_dict.get('추천도구')
            if not target_tool: continue

            if action_type == 'like':
                if target_tool in df['추천도구'].values:
                    result_messages.append(f"⚠️ '{target_tool}'(중복)")
                else:
                    data_dict['비추천수'] = 0
                    new_row = pd.DataFrame([data_dict])
                    df = pd.concat([df, new_row], ignore_index=True)
                    result_messages.append(f"✅ '{target_tool}'")
                    has_change = True

            elif action_type == 'dislike':
                if target_tool not in df['추천도구'].values:
                    result_messages.append(f"❓ '{target_tool}'(없음)")
                else:
                    idx = df[df['추천도구'] == target_tool].index
                    df.loc[idx, '비추천수'] += 1
                    current_dislikes = df.loc[idx, '비추천수'].values[0]
                    
                    if current_dislikes >= 3:
                        df = df.drop(idx)
                        result_messages.append(f"🗑️ '{target_tool}' 삭제")
                    else:
                        result_messages.append(f"📉 '{target_tool}'({current_dislikes}/3)")
                    has_change = True

        if has_change:
            df.to_csv(CSV_FILE_PATH, index=False, encoding='utf-8-sig')
            
        final_msg = ", ".join(result_messages)
        return True, final_msg

    except Exception as e:
        return False, f"오류 발생: {str(e)}"

# ==========================================
# 3. 사이드바 (UI)
# ==========================================
with st.sidebar:
    st.title("🎛️ 추천 옵션")
    
    if "sb_job" not in st.session_state:
        st.session_state.sb_job = "직접 입력"
    if "sb_situation" not in st.session_state:
        st.session_state.sb_situation = "직접 입력"

    selected_job = "직접 입력"
    selected_situation = "직접 입력"
    
    if df_tools is not None:
        st.success(f"✅ DB 연동됨 ({len(df_tools)}개 도구)")
        
        job_list = sorted(df_tools['직무'].unique().tolist())
        selected_job = st.selectbox("직무를 선택하세요", ["직접 입력"] + job_list, key="sb_job")
        
        if selected_job != "직접 입력":
            situation_list = sorted(df_tools[df_tools['직무'] == selected_job]['상황'].unique().tolist())
            selected_situation = st.selectbox("어떤 상황인가요?", ["직접 입력"] + situation_list, key="sb_situation")
    else:
        st.error("CSV 파일을 찾지 못했습니다.")
    
    st.divider()
    
    output_format = st.multiselect(
        "필요한 결과물 양식",
        ["보고서(텍스트)", "PPT(발표자료)", "이미지", "영상", "표(Excel)", "요약본"],
        default=[]
    )
    
    st.caption("ⓒ 2024 Job-Fit AI Navigator")

# ==========================================
# 4. AI 모델 설정 (하이브리드 추천)
# ==========================================
csv_context = ""
if df_tools is not None:
    display_cols = [col for col in df_tools.columns if col != '비추천수']
    csv_context = f"""
    [우리가 보유한 검증된 도구 목록 (DB)]
    {df_tools[display_cols].to_string(index=False)}
    """

sys_instruction = f"""
너는 트렌디하고 스마트한 'AI 도구 큐레이터'야.
사용자의 직무와 상황을 듣고 가장 '적합한' 도구를 추천해줘.

### 🎯 핵심 추천 전략:
1. **하이브리드 추천:** [검증된 도구 목록]을 참고하되, 목록에 없더라도 네가 알고 있는 최신/고성능 도구가 있다면 적극적으로 추천해줘.
2. **비율:** 가능하면 **(DB에 있는 도구) + (새로운 도구)**를 섞어서 제안해줘.
3. **판단 기준:** 무조건 **'사용자 상황 해결'**이 1순위야.

### 📝 답변 작성 포맷:
1. **공감 및 분석:** 상황에 대한 짧은 공감
2. **추천 도구 (1~3개):**
   - 🔧 **도구명:** (정확한 명칭)
   - 💡 **추천 이유:** (이 상황에 왜 강점인지)
   - 💰 **가격:** (무료 / 유료 / 부분유료)
   - 🔗 **링크:** (URL)
   - ✨ **꿀팁:** (실무 활용 팁)

3. **마무리:** "이 도구가 마음에 드시면 👍를 눌러주세요! 다음에 기억해 둘게요."

{csv_context}
"""

model = genai.GenerativeModel('gemini-2.5-pro', system_instruction=sys_instruction)

# ==========================================
# 5. 메인 채팅 인터페이스
# ==========================================
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

마음에 드는 추천에는 **따봉(👍)**을 눌러주시면 제가 꼭 기억해 둘게요!
(도움이 되셨다면 [GitHub](https://github.com/Timber-Kim/Job-Fit-AI-Navigator)에서 **Star(⭐)**도 부탁드려요!)
"""
st.markdown(welcome_msg)

if "messages" not in st.session_state:
    st.session_state.messages = []

# 대화 내용 표시
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        if message["role"] == "assistant":
            col_a, col_b, col_empty = st.columns([1, 1, 8])
            btn_key_like = f"like_{i}"
            btn_key_dislike = f"dislike_{i}"
            
            with col_a:
                if st.button("👍 추천", key=btn_key_like, help="이 도구를 CSV에 자동 추가"):
                    if i > 0:
                        user_query = st.session_state.messages[i-1]["content"]
                        ai_answer = message["content"]
                        with st.spinner("💾 학습 중..."):
                            success, msg = extract_and_update_csv('like', user_query, ai_answer)
                            if success:
                                st.toast(msg, icon="🎉")
                                st.cache_data.clear()
                            else:
                                st.error(msg)
                    else:
                        st.warning("저장할 이전 질문이 없습니다.")

            with col_b:
                if st.button("👎 별로", key=btn_key_dislike, help="3회 누적 시 삭제"):
                    if i > 0:
                        user_query = st.session_state.messages[i-1]["content"]
                        ai_answer = message["content"]
                        with st.spinner("처리 중..."):
                            success, msg = extract_and_update_csv('dislike', user_query, ai_answer)
                            if success:
                                st.toast(msg, icon="📉")
                                st.cache_data.clear()
                            else:
                                st.error(msg)
                    else:
                        st.warning("처리할 질문이 없습니다.")

# [콜백 함수 - 수정됨] 사이드바 초기화만 하고 대화는 유지!
def handle_quick_recommendation(job, situation):
    auto_prompt = f"나는 '{job}' 직무를 맡고 있어. 현재 '{situation}' 업무를 해야 하는데 적합한 AI 도구를 추천해줘."
    # [변경] 기존 대화를 덮어쓰지 않고 추가(append)합니다.
    st.session_state.messages.append({"role": "user", "content": auto_prompt})
    # 사이드바는 초기화해서 버튼 숨기기
    st.session_state["sb_job"] = "직접 입력"
    st.session_state["sb_situation"] = "직접 입력"

# [콜백 함수] 완전히 새로운 대화 시작 (화면 비우기)
def reset_conversation():
    st.session_state.messages = []
    st.session_state["sb_job"] = "직접 입력"
    st.session_state["sb_situation"] = "직접 입력"

# ------------------------------------------------------------------
# 버튼 영역
# ------------------------------------------------------------------
col1, col2 = st.columns([8, 2])

with col2:
    # 수동 초기화 버튼
    st.button("🔄 새로운 대화 시작", on_click=reset_conversation, use_container_width=True)

with col1:
    # 빠른 질문 버튼
    if selected_job != "직접 입력" and selected_situation != "직접 입력":
        btn_label = f"🔍 '{selected_job}' - '{selected_situation}' 추천받기"
        st.button(btn_label, type="primary", on_click=handle_quick_recommendation, args=(selected_job, selected_situation), use_container_width=True)

# ------------------------------------------------------------------
# 직접 질문 입력
# ------------------------------------------------------------------
if prompt := st.chat_input("직접 질문하기 (예: 무료로 쓸 수 있는 PPT 도구 있어?)"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

# ------------------------------------------------------------------
# AI 답변 생성 로직
# ------------------------------------------------------------------
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        with st.spinner("AI가 생각 중입니다..."):
            try:
                full_history = [m for m in st.session_state.messages if m["role"] != "system"]
                past_history = full_history[:-1]
                
                # 안전장치
                valid_history = []
                if past_history:
                    if past_history[-1]["role"] == "user":
                        valid_history = [] 
                    else:
                        valid_history = [{"role": m["role"], "parts": [m["content"]]} for m in past_history]

                chat = model.start_chat(history=valid_history)
                response = chat.send_message(st.session_state.messages[-1]["content"])
                
                message_placeholder.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun()
                
            except Exception as e:
                message_placeholder.error(f"오류가 발생했습니다. 다시 시도해 주세요. (Error: {e})")
                if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
                     st.session_state.messages.pop()
                st.rerun()