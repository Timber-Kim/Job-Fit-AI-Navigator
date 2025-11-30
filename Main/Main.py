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

# CSV 파일 경로
CSV_FILE_PATH = 'ai_tools.csv'

# 데이터 로드 함수 (비추천수 컬럼 관리 포함)
@st.cache_data
def load_data():
    target_file = CSV_FILE_PATH
    found_path = None

    if not os.path.exists(CSV_FILE_PATH):
        return None
    try:
        # 옵션 설명: 
        # encoding='utf-8-sig': 엑셀로 저장한 CSV의 깨짐 방지 (BOM 처리)
        # on_bad_lines='skip': 칸 수가 안 맞는 불량 행은 쿨하게 패스
        df = pd.read_csv(found_path, encoding='utf-8-sig', on_bad_lines='skip')
        return df
    except Exception as e_utf8:
        # 혹시 UTF-8이 아니라고 할까봐 CP949도 대비
        try:
            df = pd.read_csv(found_path, encoding='cp949', on_bad_lines='skip')
            return df
        except Exception as e_final:
            st.error(f"❌ 읽기 실패. 파일 내용이나 인코딩을 확인해주세요.")
            st.error(f"상세 에러: {e_final}")
    try:
        df = pd.read_csv(CSV_FILE_PATH, encoding='utf-8-sig', on_bad_lines='skip')
        
        # [중요] '비추천수' 컬럼이 없으면 0으로 초기화해서 생성
        if '비추천수' not in df.columns:
            df['비추천수'] = 0
            # 다시 저장해서 컬럼 확정
            df.to_csv(CSV_FILE_PATH, index=False, encoding='utf-8-sig')
            
        return df
    except:
        try:
            df = pd.read_csv(CSV_FILE_PATH, encoding='cp949', on_bad_lines='skip')
            if '비추천수' not in df.columns:
                df['비추천수'] = 0
                df.to_csv(CSV_FILE_PATH, index=False, encoding='utf-8-sig')
            return df
        except:
            return None

df_tools = load_data()

# ==========================================
# 2. (핵심 기능) AI 정보 추출 및 CSV 업데이트 로직
# ==========================================
def extract_and_update_csv(action_type, user_text, ai_text):
    """
    action_type: 'like' (추가) 또는 'dislike' (삭제 카운트)
    """
    try:
        # 1. AI를 이용해 대화 내용에서 '도구 이름'과 '정보' 추출
        extractor_model = genai.GenerativeModel('gemini-2.5-Pro')
        
        extraction_prompt = f"""
        너는 데이터 추출기야. 아래 대화를 분석해서 정보를 JSON으로 줘.
        
        [대화]
        Q: {user_text}
        A: {ai_text}
        
        [요청사항]
        1. AI가 추천한 핵심 '추천도구'(이름)을 정확히 찾아줘.
        2. 만약 action이 'like'라면, 직무, 상황, 결과물, 특징_및_팁, 유료여부, 링크 정보도 추출해.
        3. 직무/상황/결과물은 질문 내용을 바탕으로 추론해.
        
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

        # CSV 파일 열기
        if os.path.exists(CSV_FILE_PATH):
            df = pd.read_csv(CSV_FILE_PATH, encoding='utf-8-sig', on_bad_lines='skip')
        else:
            df = pd.DataFrame(columns=['직무','상황','결과물','추천도구','특징_및_팁','유료여부','링크','비추천수'])

        # '비추천수' 컬럼 안전장치
        if '비추천수' not in df.columns:
            df['비추천수'] = 0

        # ==========================================
        # CASE 1: 👍 좋아요 (데이터 추가)
        # ==========================================
        if action_type == 'like':
            # 이미 있는 도구인지 확인 (중복 방지)
            if target_tool in df['추천도구'].values:
                return False, f"'{target_tool}'은(는) 이미 데이터베이스에 있습니다."
            
            # 새 데이터 추가 (비추천수는 0으로 시작)
            data_dict['비추천수'] = 0
            new_row = pd.DataFrame([data_dict])
            df_updated = pd.concat([df, new_row], ignore_index=True)
            df_updated.to_csv(CSV_FILE_PATH, index=False, encoding='utf-8-sig')
            return True, f"'{target_tool}' 정보가 자동으로 학습되었습니다!"

        # ==========================================
        # CASE 2: 👎 싫어요 (비추천 카운트 증가 & 삭제)
        # ==========================================
        elif action_type == 'dislike':
            # 데이터베이스에 있는 도구인지 확인
            if target_tool not in df['추천도구'].values:
                return False, f"'{target_tool}'은(는) 데이터베이스에 없는 도구라 삭제할 수 없습니다."
            
            # 비추천수 증가
            idx = df[df['추천도구'] == target_tool].index
            df.loc[idx, '비추천수'] += 1
            current_dislikes = df.loc[idx, '비추천수'].values[0]
            
            msg = ""
            # 3회 이상이면 삭제
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
    
    # [새로운 기능] CSV 기반 직무/상황 선택 기능
    selected_job = "직접 입력"
    selected_situation = "직접 입력"
    
    if df_tools is not None:
        # 1. 직무 목록 추출 (중복 제거 및 정렬)
        job_list = sorted(df_tools['직무'].unique().tolist())
        # '직접 입력' 옵션을 맨 앞에 추가
        selected_job = st.selectbox("직무를 선택하세요", ["직접 입력"] + job_list)
        
        # 2. 선택한 직무에 맞는 상황 목록만 필터링
        if selected_job != "직접 입력":
            # 해당 직무의 상황 데이터만 가져오기
            situation_list = sorted(df_tools[df_tools['직무'] == selected_job]['상황'].unique().tolist())
            selected_situation = st.selectbox("어떤 상황인가요?", ["직접 입력"] + situation_list)
    
    st.divider()
    
    # 결과물 양식 선택 (기존 유지)
    output_format = st.multiselect(
        "필요한 결과물 양식",
        ["보고서(텍스트)", "PPT(발표자료)", "이미지", "영상", "표(Excel)", "요약본"],
        default=[]
    )
    
    st.info("💡 팁: 직무와 상황을 선택하고 '자동 질문 생성' 버튼을 누르면 편합니다.")
    
    # 대화 초기화 버튼
    if st.button("🗑️ 대화 내용 초기화"):
        st.session_state.messages = []
        st.rerun()

# ==========================================
# 4. AI 모델 설정
# ==========================================
csv_context = ""
if df_tools is not None:
    # 비추천수 컬럼은 AI에게 굳이 보여줄 필요 없으므로 제외하고 전달 가능 (선택사항)
    display_cols = [col for col in df_tools.columns if col != '비추천수']
    csv_context = f"""
    [내부 AI 도구 데이터베이스]
    {df_tools[display_cols].to_string(index=False)}
    """

sys_instruction = f"""
너는 '직무/상황별 AI 도구 추천 전문가'야. 
사용자의 직무와 상황을 듣고, [내부 AI 도구 데이터베이스]를 최우선으로 참고하여 도구를 추천해줘.

### 🎯 답변 원칙:
1. **데이터 우선:** 데이터베이스에 있는 도구라면 내용을 참고해. 없으면 외부 지식을 활용해.
2. **형식:** '표(Table)' 또는 '글머리 기호' 사용.
3. **사용자 필터:** {', '.join(output_format) if output_format else '전체'} 양식 고려.
4. **필수 포함:** 도구명, 추천 이유, 유료여부, 링크

{csv_context}
"""

# Gemini 1.5 Pro 사용 (2.5는 아직 비공개 모델일 수 있어 1.5로 설정)
model = genai.GenerativeModel('gemini-2.5-pro', system_instruction=sys_instruction)

# ==========================================
# 5. 메인 채팅 인터페이스
# ==========================================
st.title("🚀 Job-Fit AI 네비게이터")
st.caption("당신의 업무 상황을 말해주세요. 최적의 AI 도구를 찾아드립니다.")

# 대화 기록 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 대화 내용 표시
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # [핵심] AI 답변인 경우 좋아요/싫어요 버튼 표시
        if message["role"] == "assistant":
            col_a, col_b, col_empty = st.columns([1, 1, 8])
            
            # 고유 키(key) 생성
            btn_key_like = f"like_{i}"
            btn_key_dislike = f"dislike_{i}"
            
            with col_a:
                if st.button("👍 추천", key=btn_key_like, help="이 도구를 CSV에 자동 추가합니다."):
                    user_query = st.session_state.messages[i-1]["content"] if i > 0 else "질문 없음"
                    ai_answer = message["content"]
                    
                    with st.spinner("💾 데이터베이스에 학습시키는 중..."):
                        success, msg = extract_and_update_csv('like', user_query, ai_answer)
                        if success:
                            st.toast(msg, icon="🎉")
                            st.cache_data.clear() # 데이터 갱신
                        else:
                            st.error(msg)
                            
            with col_b:
                if st.button("👎 별로", key=btn_key_dislike, help="3회 누적 시 CSV에서 삭제됩니다."):
                    user_query = st.session_state.messages[i-1]["content"] if i > 0 else "질문 없음"
                    ai_answer = message["content"]
                    
                    with st.spinner("🗑️ 비추천 처리 중..."):
                        success, msg = extract_and_update_csv('dislike', user_query, ai_answer)
                        if success:
                            st.toast(msg, icon="📉")
                            st.cache_data.clear()
                        else:
                            st.error(msg)

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

# AI 답변 생성
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        with st.spinner("AI가 생각 중입니다..."):
            try:
                chat_history = [{"role": m["role"], "parts": [m["content"]]} for m in st.session_state.messages if m["role"] != "system"]
                chat = model.start_chat(history=chat_history[:-1])
                response = chat.send_message(st.session_state.messages[-1]["content"])
                
                message_placeholder.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun() # 버튼 생성을 위해 새로고침
            except Exception as e:
                message_placeholder.error(f"오류 발생: {e}")
                st.rerun() # 버튼 생성을 위해 새로고침