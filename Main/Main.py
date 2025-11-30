import streamlit as st
import google.generativeai as genai
import pandas as pd
import os
import json

# ==========================================
# 1. 기본 설정 및 데이터 로드
# ==========================================
st.set_page_config(page_title="Job-Fit AI", page_icon="🤖", layout="wide")

try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    GOOGLE_API_KEY = "여기에_API_키를_입력하세요" # 로컬 테스트용

genai.configure(api_key=GOOGLE_API_KEY)

# 데이터 로드 함수
@st.cache_data
def load_data():
    target_file = 'ai_tools.csv'
    # 탐정 모드로 파일 찾기
    found_path = None
    for root, dirs, files in os.walk(os.getcwd()):
        if target_file in files:
            found_path = os.path.join(root, target_file)
            break
    
    if found_path is None:
        parent_dir = os.path.dirname(os.getcwd())
        for root, dirs, files in os.walk(parent_dir):
            if target_file in files:
                found_path = os.path.join(root, target_file)
                break

    if found_path is None: return None

    try:
        df = pd.read_csv(found_path, encoding='utf-8-sig', on_bad_lines='skip')
        return df
    except:
        try:
            df = pd.read_csv(found_path, encoding='cp949', on_bad_lines='skip')
            return df
        except:
            return None

df_tools = load_data()

# ==========================================
# 2. (핵심 기능) AI 답변을 CSV 데이터로 자동 변환 및 저장
# ==========================================
def auto_save_to_csv(user_text, ai_text):
    """
    AI가 대화 내용을 분석하여 CSV 양식에 맞는 JSON으로 변환 후 저장
    """
    try:
        # 1. 정보를 추출하기 위한 전용 AI 모델 호출
        extractor_model = genai.GenerativeModel('gemini-2.5-pro')
        
        extraction_prompt = f"""
        너는 '데이터 추출 전문가'야. 아래 대화 내용을 분석해서 AI 도구 정보를 JSON 형식으로 추출해줘.
        
        [대화 내용]
        사용자 질문: {user_text}
        AI 답변: {ai_text}
        
        [추출할 필드]
        - 직무: (질문에서 유추, 모르면 '기타')
        - 상황: (질문 내용 요약)
        - 결과물: (질문에서 유추, 예: 보고서, 이미지, PPT 등)
        - 추천도구: (답변에서 추천한 핵심 도구 이름 1개만)
        - 특징_및_팁: (답변 내용 요약)
        - 유료여부: (답변에 있으면 작성, 없으면 '확인필요')
        - 링크: (답변에 URL이 있다면 추출, 없으면 빈칸)

        반드시 오직 JSON 데이터만 출력해. (Markdown 태그 없이)
        """
        
        # 정보 추출 실행
        result = extractor_model.generate_content(extraction_prompt)
        cleaned_json = result.text.replace("```json", "").replace("```", "").strip()
        data_dict = json.loads(cleaned_json)
        
        # 2. CSV 파일에 저장
        file_path = 'ai_tools.csv'
        
        # 기존 파일 위치 찾기 (load_data 로직 재사용하거나 경로 고정)
        # 편의상 현재 작업 경로 우선 탐색
        if not os.path.exists(file_path):
             # 없으면 새로 생성
             df_new = pd.DataFrame([data_dict])
             df_new.to_csv(file_path, index=False, encoding='utf-8-sig')
        else:
            # 있으면 추가
            df_old = pd.read_csv(file_path, encoding='utf-8-sig', on_bad_lines='skip')
            df_new = pd.DataFrame([data_dict])
            df_updated = pd.concat([df_old, df_new], ignore_index=True)
            df_updated.to_csv(file_path, index=False, encoding='utf-8-sig')
            
        return True, data_dict['추천도구']
        
    except Exception as e:
        return False, str(e)

# ==========================================
# 3. 사이드바 및 메인 설정
# ==========================================
with st.sidebar:
    st.title("🎛️ 메뉴")
    if df_tools is not None:
        st.success(f"데이터 연동됨 ({len(df_tools)}개)")
    
    if st.button("대화 초기화"):
        st.session_state.messages = []
        st.rerun()

# AI 모델 설정 (메인 답변용)
csv_context = ""
if df_tools is not None:
    csv_context = f"[내부 데이터베이스]\n{df_tools.to_string(index=False)}"

sys_instruction = f"""
너는 직무별 AI 도구 추천 전문가야. 
[내부 데이터베이스]를 우선 참고하고, 없으면 외부 지식을 활용해.
답변에는 반드시 도구 이름, 추천 이유, 유료 여부, 링크를 포함해줘.
{csv_context}
"""
model = genai.GenerativeModel('gemini-2.5-pro', system_instruction=sys_instruction)

# ==========================================
# 4. 메인 채팅 인터페이스
# ==========================================
st.title("🚀 Job-Fit AI (자동학습 버전)")
st.caption("질문하고 👍를 누르면, AI가 자동으로 학습하여 데이터베이스에 추가합니다.")

if "messages" not in st.session_state:
    st.session_state.messages = []

# 대화 내용 표시
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # [핵심] AI의 답변인 경우에만 '좋아요' 버튼 표시
        if message["role"] == "assistant":
            # 이미 저장된 메시지인지 확인하기 위한 키 관리 (버튼 중복 클릭 방지 등은 심화 구현 필요)
            col1, col2 = st.columns([1, 10])
            with col1:
                # 고유한 key 생성을 위해 인덱스(i) 사용
                if st.button("👍", key=f"like_{i}", help="이 답변을 데이터베이스에 자동 저장"):
                    # 바로 직전의 사용자 질문 찾기
                    user_query = st.session_state.messages[i-1]["content"] if i > 0 else "질문 없음"
                    ai_answer = message["content"]
                    
                    with st.spinner("💾 답변 내용을 분석하여 CSV에 저장 중..."):
                        success, tool_name = auto_save_to_csv(user_query, ai_answer)
                        if success:
                            st.toast(f"✅ '{tool_name}' 정보가 CSV에 저장되었습니다!", icon="🎉")
                            st.cache_data.clear() # 데이터 갱신을 위해 캐시 삭제
                        else:
                            st.error(f"저장 실패: {tool_name}")

# 사용자 입력 처리
if prompt := st.chat_input("필요한 AI 도구를 물어보세요"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun() # 화면 갱신 후 답변 생성 로직으로 이동

# 답변 생성 로직
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        with st.spinner("도구를 찾는 중..."):
            chat_history = [{"role": m["role"], "parts": [m["content"]]} for m in st.session_state.messages if m["role"] != "system"]
            
            chat = model.start_chat(history=chat_history[:-1])
            response = chat.send_message(st.session_state.messages[-1]["content"])
            
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            st.rerun() # 답변 완료 후 버튼을 그리기 위해 다시 갱신