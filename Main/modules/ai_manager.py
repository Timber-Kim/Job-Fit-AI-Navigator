import streamlit as st
import google.generativeai as genai
from google.api_core import exceptions
import time
import json
from .config import SYSTEM_PROMPT_TEMPLATE, MODEL_NAME
import difflib

# ---------------------------------------------------------
# 1. 제미나이 설정
# ---------------------------------------------------------
def configure_genai():
    try:
        api_key = None
        
        # 1. 사용자 입력 키 우선 사용 (공백도 제거하여 유효성 확인)
        user_key_input = st.session_state.get("USER_API_KEY", "").strip()
        
        if user_key_input:
            api_key = user_key_input
        
        # 2. 사용자 키가 없으면 공용 키 사용
        elif "GOOGLE_API_KEY" in st.secrets:
            api_key = st.secrets["GOOGLE_API_KEY"]
        
        # 3. 사용할 키가 없으면 None 반환
        if not api_key:
            return None

        # 4. 키 설정 시도 (여기서 400 오류 발생 가능)
        genai.configure(api_key=api_key)
        
        return genai.GenerativeModel(MODEL_NAME, generation_config={"temperature": 0.8})
        
    except Exception as e:
        error_message = str(e)
        
        # 400 Invalid Argument (API Key Invalid) 오류 포착
        if "API key not valid" in error_message or "API_KEY_INVALID" in error_message:
            
            # 🚨 유효하지 않은 키를 입력했을 경우 (사용자 키 삭제 후 공용으로 자동 전환)
            if "USER_API_KEY" in st.session_state:
                st.error("🚨 **입력하신 사용자 API Key가 유효하지 않습니다.**\n\n자동으로 공용 키 모드로 전환되었습니다. 다시 시도하시려면 사이드바의 입력창을 비워주세요.")
                
                # 잘못된 사용자 키 삭제 (공용 키로 전환 유도)
                del st.session_state["USER_API_KEY"]
                st.rerun() 
            
            # 오류가 발생한 키가 공용 키인 경우
            elif "GOOGLE_API_KEY" in st.secrets:
                 st.error("⛔ **앱 설정 오류**: 공용 API Key가 유효하지 않습니다. 개발자에게 문의해주세요.")
        
        print(f"모델 설정 오류: {error_message}")
        return None

# ---------------------------------------------------------
# AI 호출 공통 처리 함수
# ---------------------------------------------------------
def call_ai_common(prompt, status_msg, output_type="text", fallback_value=None):
    """
    AI 호출, 429 오류 재시도, 400 키 오류 감지, 상태바 표시, JSON 파싱을 통합 관리
    """
    model = configure_genai()
    if not model: return fallback_value

    max_retries = 3
    wait_time = 30

    with st.status(status_msg, expanded=False) as status:
        for attempt in range(max_retries):
            try:
                # 1. AI 응답 생성
                response = model.generate_content(prompt)
                text = response.text.strip()

                # 2. 마크다운 코드블럭 제거
                if "```" in text:
                    text = text.replace("```json", "").replace("```", "")

                # 3. 결과 반환 처리 (JSON/Text)
                if output_type == "json":
                    try:
                        result = json.loads(text)
                        if isinstance(fallback_value, list) and isinstance(result, dict):
                            result = [result]
                        
                        status.update(label="✅ 처리 완료!", state="complete", expanded=False)
                        return result
                    except json.JSONDecodeError:
                        print(f"JSON 파싱 실패: {text}")
                        status.update(label="⚠️ 데이터 형식 오류", state="error")
                        return fallback_value
                else:
                    status.update(label="✅ 처리 완료!", state="complete", expanded=False)
                    return text

            # 400 API Key 오류 처리
            except exceptions.InvalidArgument as e:
                err_msg = str(e)
                if "API key not valid" in err_msg or "API_KEY_INVALID" in err_msg:
                    # 사용자에게 명확한 에러 메시지 표시
                    status.update(label="⛔ API 키 오류!", state="error")
                    st.error("🚨 **입력하신 API Key가 올바르지 않습니다.**\n\n오타가 없는지, 공백이 들어가지 않았는지 확인해 주세요. (사이드바에서 키를 지우면 공용 키로 자동 전환됩니다.)")
                    return fallback_value
                else:
                    # 진짜 요청 내용이 잘못된 경우
                    status.update(label="❌ 잘못된 요청입니다 (400)", state="error")
                    return fallback_value

            # 429 사용량 초과 처리
            except exceptions.ResourceExhausted:
                msg = f"⏳ 사용량이 많아 잠시 대기 중입니다... ({attempt + 1}/{max_retries})"
                status.update(label=msg, state="running")
                time.sleep(wait_time)

            # 기타 오류 처리
            except Exception as e:
                print(f"AI 호출 중 오류: {e}")
                status.update(label="❌ 오류 발생", state="error")
                return fallback_value

    # 재시도 횟수 초과 시
    status.update(label="❌ 응답 시간 초과 (재시도 실패)", state="error")
    return fallback_value


# ---------------------------------------------------------
# 2. 메인 AI 답변 생성
# ---------------------------------------------------------

# 1시간까지 메모리에 저장
@st.cache_data(show_spinner=False, ttl=3600)
def get_ai_response(messages, df_tools):
    model = configure_genai()
    if not model: 
        return "⚠️ API Key 설정 오류: secrets.toml 파일을 확인해주세요."

    csv_context = ""
    if not df_tools.empty:
        # 1. AI 판단에 불필요한 컬럼 제거 (예: 타임스탬프, 긴 설명 등)
        essential_cols = ['추천도구', '직무', '상황', '특징_및_팁', '추천수', '비추천수', '링크']
        
        # 실제 데이터프레임에 있는 컬럼만 교집합으로 선택 (에러 방지)
        target_cols = [c for c in essential_cols if c in df_tools.columns]
        
        csv_context = df_tools[target_cols].to_string(index=False)
    
    full_prompt = SYSTEM_PROMPT_TEMPLATE.format(csv_context=csv_context)
    model = genai.GenerativeModel(MODEL_NAME, system_instruction=full_prompt)

    history = [
        {"role": "user" if m["role"]=="user" else "model", "parts": [m["content"]]} 
        for m in messages[:-1]
    ]
    
    # 여기는 Main.py의 get_ai_response_safe 함수에서 에러를 잡으므로 try-except 생략
    chat = model.start_chat(history=history)
    response = chat.send_message(messages[-1]["content"])
    
    return response.text


# ---------------------------------------------------------
# 3. 도구 정보 추출
# ---------------------------------------------------------
def parse_tools(user_question, ai_answer):
    prompt = f"""
    사용자의 질문: {user_question}
    AI의 답변: {ai_answer}
    
    위 내용에서 추천된 'AI 도구'들의 정보를 다음 JSON 형식의 리스트로 추출해줘.
    형식: [{{ "추천도구": "도구명", "직무": "관련직무", "상황": "사용상황", "결과물": "예상결과물", "특징_및_팁": "한줄설명", "유료여부": "유료/무료/부분유료", "링크": "URL(없으면 공란)" }}]
    
    1. 도구 이름이 명확하지 않으면 빈 리스트 [] 를 반환하세요.
    2. 부연 설명 없이 JSON만 출력하세요.
    """

    return call_ai_common(
        prompt=prompt,
        status_msg="🛠️ 답변 내용을 분석하여 도구를 추출하고 있습니다...",
        output_type="json",
        fallback_value=[]
    )


# ---------------------------------------------------------
# 4. 직무 표준화
# ---------------------------------------------------------
def normalize_job_category(input_job, existing_jobs):
    """
    AI를 쓰지 않고, 파이썬 문자열 비교를 통해 직무를 표준화합니다.
    (API 비용 절감 및 속도 향상)
    """
    input_job = input_job.strip()
    
    # 1. 완벽하게 일치하는 직무가 있으면 바로 반환
    if input_job in existing_jobs:
        return input_job

    # 2. 유사도 검사 (오타 수정 정도의 역할)
    #    existing_jobs 중에서 input_job과 가장 비슷한 단어 1개를 찾음 (유사도 0.6 이상)
    matches = difflib.get_close_matches(input_job, existing_jobs, n=1, cutoff=0.6)
    
    if matches:
        return matches[0] # 가장 비슷한 기존 직무 반환

    # 3. 매칭되는 게 없으면 그냥 새로운 직무로 인정하고 그대로 반환
    return input_job
