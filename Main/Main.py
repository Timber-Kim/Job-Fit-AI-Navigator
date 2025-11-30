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
    GOOGLE_API_KEY = "여기에_새로_발급받은_API_키를_넣으세요" 

genai.configure(api_key=GOOGLE_API_KEY)

# [수정 1] 파일 경로를 절대 경로로 잡아서 무조건 찾게 함
current_dir = os.path.dirname(os.path.abspath(__file__))
CSV_FILE_PATH = os.path.join(current_dir, 'ai_tools.csv')

# 데이터 로드 함수
@st.cache_data
def load_data():
    if not os.path.exists(CSV_FILE_PATH):
        st.error(f"❌ 파일을 찾을 수 없습니다: {CSV_FILE_PATH}")
        return None

    try:
        # 1차 시도: utf-8-sig (엑셀 호환)
        df = pd.read_csv(CSV_FILE_PATH, encoding='utf-8-sig', on_bad_lines='skip')
    except:
        try:
            # 2차 시도: cp949 (한글 윈도우)
            df = pd.read_csv(CSV_FILE_PATH, encoding='cp949', on_bad_lines='skip')
        except Exception as e:
            st.error(f"❌ 파일 읽기 실패: {e}")
            return None

    # [중요] '비추천수' 컬럼 관리
    if df is not None:
        if '비추천수' not in df.columns:
            df['비추천수'] = 0
            df.to_csv(CSV_FILE_PATH, index=False, encoding='utf-8-sig')
            
    return df

df_tools = load_data()

# ==========================================
# 2. (핵심 기능) AI 정보 추출 및 CSV 업데이트 로직
# ==========================================
def extract_and_update_csv(action_type, user_text, ai_text):
    try:
        # [수정 2] 모델명을 2.5(존재X) -> 1.5-flash(빠름)로 변경
        extractor_model = genai.GenerativeModel('gemini-2.5-pro')
        
        extraction_prompt = f"""
        너는 데이터 추출기야. 아래 대화를 분석해서 정보를 JSON으로 줘.
        
        [대화]
        Q: {user_text}
        A: {ai_text}
        
        [요청사항]
        1. AI 답변에서 추천한 핵심 '추천도구'(이름)을 정확히 찾아줘.
        2. action이 'like'라면, 질문과 답변을 바탕으로 직무, 상황, 결과물, 특징_및_팁, 유료여부, 링크 정보도 추출해.
        
        출력 포맷(JSON):
        {{
            "추천도구": "도구이름",
            "직무": "...",
            "상황": "...",
            "결과물": "...",
            "특징_및_팁": "...",
            "유료여부": "...",
            "링크": "..."
        }}
        오직 JSON만 출력해.
        """
        
        result = extractor_model.generate_content(extraction_prompt)
        cleaned_json = result.text.replace("```json", "").replace("```", "").strip()
        data_dict = json.loads(cleaned_json)
        target_tool = data_dict.get('추천도구')

        # 파일 다시 읽기 (최신 상태)
        if os.path.exists(CSV_FILE_PATH):
            df = pd.read_csv(CSV_FILE_PATH, encoding='utf-8-sig', on_bad_lines='skip')
        else:
            return False, "CSV 파일이 없습니다."

        if '비추천수' not in df.columns:
            df['비추천수'] = 0

        # CASE 1: 👍 좋아요
        if action_type == 'like':
            if target_tool in df['추천도구'].values:
                return False, f"'{target_tool}'은(는) 이미 데이터베이스에 있습니다."
            
            data_dict['비추천수'] = 0
            new_row = pd.DataFrame([data_dict])
            df_updated = pd.concat([df, new_row], ignore_index=True)
            df_updated.to_csv(CSV_FILE_PATH, index=False, encoding='utf-8-sig')
            return True, f"'{target_tool}' 정보가 학습되었습니다!"

        # CASE 2: 👎 싫어요
        elif action_type == 'dislike':
            if target_tool not in df['추천도구'].values:
                return False, f"'{target_tool}'은(는) 데이터베이스에 없는 도구라 삭제할 수 없습니다."
            
            idx = df[df['추천도구'] == target_tool].index
            df.loc[idx, '비추천수'] += 1
            current_dislikes = df.loc[idx, '비추천수'].values[0]
            
            msg = ""
            if current_dislikes >= 3:
                df = df.drop(idx)
                msg = f"'{target_tool}'이(가) 비추천 3회 누적으로 삭제되었습니다. 🗑️"
            else:
                msg = f"'{target_tool}' 비추천 처리됨. (현재 {current_dislikes}/3회) 👎"
            
            df.to_csv(CSV_FILE_PATH, index=False, encoding='utf-8-sig')
            return True, msg

    except Exception as e:
        return False, f"오류 발생: {str(e)}"

# ==========================================
# 3. 사이드바 (UI)
# ==========================================
with st.sidebar:
    st.title("🎛️ 추천 옵션")
    
    selected_job = "직접 입력"
    selected_situation = "직접 입력"
    
    if df_tools is not None:
        # 데이터 연동 확인 표시
        st.success(f"✅ DB 연동됨 ({len(df_tools)}개 도구)")
        
        job_list = sorted(df_tools['직무'].unique().tolist())
        selected_job = st.selectbox("직무를 선택하세요", ["직접 입력"] + job_list)
        
        if selected_job != "직접 입력":
            situation_list = sorted(df_tools[df_tools['직무'] == selected_job]['상황'].unique().tolist())
            selected_situation = st.selectbox("어떤 상황인가요?", ["직접 입력"] + situation_list)
    else:
        st.error("CSV 파일을 찾지 못했습니다.")
    
    st.divider()
    
    output_format = st.multiselect(
        "필요한 결과물 양식",
        ["보고서(텍스트)", "PPT(발표자료)", "이미지", "영상", "표(Excel)", "요약본"],
        default=[]
    )
    
    if st.button("🗑️ 대화 내용 초기화"):
        st.session_state.messages = []
        st.rerun()

# ==========================================
# 4. AI 모델 설정 (메인 챗봇)
# ==========================================
csv_context = ""
if df_tools is not None:
    display_cols = [col for col in df_tools.columns if col != '비추천수']
    csv_context = f"""
    [내부 AI 도구 데이터베이스]
    {df_tools[display_cols].to_string(index=False)}
    """

sys_instruction = f"""
너는 '직무/상황별 AI 도구 추천 전문가'야. 
사용자의 직무와 상황을 듣고, [내부 AI 도구 데이터베이스]를 최우선으로 참고하여 도구를 추천해줘.

### 🎯 답변 원칙:
1. **데이터 우선:** 데이터베이스 내용을 참고하되, 없으면 외부 지식을 활용해.
2. **형식:** '표(Table)' 또는 '글머리 기호' 사용.
3. **사용자 필터:** {', '.join(output_format) if output_format else '전체'} 양식 고려.
4. **필수 포함:** 도구명, 추천 이유, 유료여부, 링크

{csv_context}
"""

# [수정 3] 메인 모델도 2.5 -> 1.5-pro로 변경
model = genai.GenerativeModel('gemini-2.5-pro', system_instruction=sys_instruction)

# ==========================================
# 5. 메인 채팅 인터페이스
# ==========================================
st.title("🚀 Job-Fit AI 네비게이터")
welcome_msg = """
👋 **반가워요! 당신의 스마트한 업무 파트너, Job-Fit AI입니다.**
"""

st.caption(welcome_msg)

# 대화 기록 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 대화 내용 표시
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # AI 답변 하단에 버튼 표시
        if message["role"] == "assistant":
            col_a, col_b, col_empty = st.columns([1, 1, 8])
            
            btn_key_like = f"like_{i}"
            btn_key_dislike = f"dislike_{i}"
            
            with col_a:
                if st.button("👍 추천", key=btn_key_like, help="이 도구를 CSV에 자동 추가"):
                    # user_query가 없는 경우(첫 인사 등) 방지
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

# 빠른 질문 버튼
if selected_job != "직접 입력" and selected_situation != "직접 입력":
    btn_label = f"🔍 '{selected_job}' - '{selected_situation}' 추천받기"
    if st.button(btn_label, type="primary"):
        auto_prompt = f"나는 '{selected_job}' 직무를 맡고 있어. 현재 '{selected_situation}' 업무를 해야 하는데 적합한 AI 도구를 추천해줘."
        st.session_state.messages.append({"role": "user", "content": auto_prompt})
        st.rerun()

# 직접 질문 입력
if prompt := st.chat_input("직접 질문하기 (예: 무료로 쓸 수 있는 PPT 도구 있어?)"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

# AI 답변 생성 로직
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        with st.spinner("AI가 생각 중입니다..."):
            try:
                chat_history = [{"role": m["role"], "parts": [m["content"]]} for m in st.session_state.messages if m["role"] != "system"]
                # chat_history가 비어있을 경우 대비
                if not chat_history:
                    chat_history = None
                
                # history 전달 시 마지막 메시지 제외 로직 점검
                # start_chat의 history는 '이전 대화'만 넣어야 하므로 [:-1]이 맞음
                history_for_model = chat_history[:-1] if chat_history else []
                
                chat = model.start_chat(history=history_for_model)
                response = chat.send_message(st.session_state.messages[-1]["content"])
                
                message_placeholder.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun()
            except Exception as e:
                message_placeholder.error(f"오류 발생: {e}")