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
        
        # 1. 사용자 입력 키 우선 사용
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
# AI 호출 공통 처리
# ---------------------------------------------------------
def call_ai_common(prompt, status_msg, output_type="text", fallback_value=None):
    """
    유료 플랜용: 불필요한 재시도를 줄이고, 로그를 상세히 출력합니다.
    """
    model = configure_genai()
    if not model: return fallback_value

    # 🚨 유료 플랜 세팅 (재시도 최소화)
    max_retries = 1      # 최대 1번만 재시도 (총 2회 시도)
    wait_time = 2        # 대기 시간 2초로 단축

    with st.status(status_msg, expanded=False) as status:
        for attempt in range(max_retries + 1): # range(2) -> 0, 1
            try:
                # [디버그 로그] 시도 횟수 출력
                print(f"🚀 [AI 호출 시도] {attempt+1}/{max_retries+1}회 차 시작...")
                
                # 1. AI 응답 생성
                response = model.generate_content(prompt)
                
                # [중요] 응답이 막혔거나 비었는지 확인
                if not response.parts:
                    print("⚠️ [경고] AI 응답이 비어있음 (Safety Filter 등 가능성)")
                    # 여기서 재시도하지 말고 멈추거나, 텍스트가 없다고 처리
                
                text = response.text.strip()
                print(f"✅ [성공] 응답 수신 완료 (길이: {len(text)})")

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
                        print(f"❌ [에러] JSON 파싱 실패: {text[:50]}...")
                        status.update(label="⚠️ 데이터 형식 오류", state="error")
                        return fallback_value
                else:
                    status.update(label="✅ 처리 완료!", state="complete", expanded=False)
                    return text

            # 400 API Key 오류 처리 (즉시 중단)
            except exceptions.InvalidArgument as e:
                print(f"⛔ [치명적 에러] API 키 오류: {e}")
                status.update(label="⛔ API 키 오류!", state="error")
                st.error("🚨 API Key가 올바르지 않습니다.")
                if "USER_API_KEY" in st.session_state:
                    del st.session_state["USER_API_KEY"]
                return fallback_value # 재시도 금지

            # 429 사용량 초과 (유료에서는 드묾)
            except exceptions.ResourceExhausted:
                print(f"⏳ [대기] 429 Rate Limit 발생. {wait_time}초 대기...")
                msg = f"잠시 숨 고르는 중... ({attempt + 1}/{max_retries + 1})"
                status.update(label=msg, state="running")
                time.sleep(wait_time)

            # 500 서버 오류 등 기타 오류
            except Exception as e:
                print(f"💥 [알 수 없는 에러] {str(e)}")
                # 마지막 시도가 아니면 잠시 대기
                if attempt < max_retries:
                     status.update(label=f"⚠️ 일시적 오류, 재시도 중...", state="running")
                     time.sleep(1)
                else:
                    status.update(label="❌ 오류 발생 (서버 응답 없음)", state="error")
                    return fallback_value

    status.update(label="❌ 응답 실패", state="error")
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
        # '비추천수' 제외하고 컨텍스트 제공
        display_cols = [c for c in df_tools.columns if c != '비추천수']
        csv_context = df_tools[display_cols].to_string(index=False)
    
    full_prompt = SYSTEM_PROMPT_TEMPLATE.format(csv_context=csv_context)
    
    # 시스템 프롬프트 적용
    model = genai.GenerativeModel(MODEL_NAME, system_instruction=full_prompt)

    history = [
        {"role": "user" if m["role"]=="user" else "model", "parts": [m["content"]]} 
        for m in messages[:-1]
    ]
    
    # ⚠️ try-except 없음 (main.py에서 429 에러 감지용)
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
