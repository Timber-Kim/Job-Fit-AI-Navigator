import streamlit as st
import google.generativeai as genai
from google.api_core import exceptions
import time
import json
from .config import SYSTEM_PROMPT_TEMPLATE, MODEL_NAME

# ---------------------------------------------------------
# 1. 제미나이 설정 (공통 사용)
# ---------------------------------------------------------
def configure_genai():
    try:
        if "GOOGLE_API_KEY" in st.secrets:
            genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        else:
            return None
            
        return genai.GenerativeModel(MODEL_NAME, generation_config={"temperature": 0.8})
    except Exception as e:
        print(f"모델 설정 오류: {e}")
        return None

# ---------------------------------------------------------
# 🛠️ [핵심] AI 호출 공통 처리 함수 (중복 제거용)
# ---------------------------------------------------------
def call_ai_common(prompt, status_msg, output_type="text", fallback_value=None):
    """
    AI 호출, 429 오류 재시도, 상태바 표시, JSON 파싱을 통합 관리하는 함수
    
    :param prompt: AI에게 보낼 질문
    :param status_msg: 상태바에 띄울 메시지
    :param output_type: "text" 또는 "json"
    :param fallback_value: 실패 시 반환할 기본값
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

                # 2. 마크다운 코드블럭 제거 (공통)
                if "```" in text:
                    text = text.replace("```json", "").replace("```", "")

                # 3. 결과 반환 처리
                if output_type == "json":
                    try:
                        result = json.loads(text)
                        
                        # 리스트가 필요한데 딕셔너리로 오면 감싸주기 (도구 추출용)
                        if isinstance(fallback_value, list) and isinstance(result, dict):
                            result = [result]
                        
                        status.update(label="✅ 처리 완료!", state="complete", expanded=False)
                        return result
                    except json.JSONDecodeError:
                        print(f"JSON 파싱 실패: {text}")
                        status.update(label="⚠️ 데이터 형식 오류", state="error")
                        return fallback_value
                
                else: # text 반환
                    status.update(label="✅ 처리 완료!", state="complete", expanded=False)
                    return text

            except exceptions.ResourceExhausted:
                # 4. 사용량 초과 시 대기 (재시도 로직)
                msg = f"⏳ 사용량이 많아 잠시 대기 중입니다... ({attempt + 1}/{max_retries})"
                status.update(label=msg, state="running")
                time.sleep(wait_time)

            except Exception as e:
                print(f"AI 호출 중 오류: {e}")
                status.update(label="❌ 오류 발생", state="error")
                return fallback_value

    # 재시도 횟수 초과 시
    status.update(label="❌ 응답 시간 초과 (재시도 실패)", state="error")
    return fallback_value


# ---------------------------------------------------------
# 2. 메인 AI 답변 생성 (채팅 히스토리 관리로 인해 별도 유지)
# ---------------------------------------------------------
def get_ai_response(messages, df_tools):
    model = configure_genai()
    if not model: 
        return "⚠️ API Key 설정 오류: secrets.toml 파일을 확인해주세요."

    csv_context = ""
    if not df_tools.empty:
        display_cols = [c for c in df_tools.columns if c != '비추천수']
        csv_context = df_tools[display_cols].to_string(index=False)
    
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
# 3. 도구 정보 추출 (리팩토링됨 ✨)
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

    # 공통 함수 호출로 30줄 -> 1줄 단축
    return call_ai_common(
        prompt=prompt,
        status_msg="🛠️ 답변 내용을 분석하여 도구를 추출하고 있습니다...",
        output_type="json",
        fallback_value=[]
    )


# ---------------------------------------------------------
# 4. 직무 표준화 (리팩토링됨 ✨)
# ---------------------------------------------------------
def normalize_job_category(input_job, existing_jobs):
    jobs_str = ", ".join(existing_jobs)
    prompt = f"""
    사용자가 입력한 직무: '{input_job}'
    현재 우리 DB에 있는 직무 목록: [{jobs_str}]
    
    [지시사항]
    1. 사용자의 입력이 기존 목록의 항목과 의미상 매우 유사하다면, 그 기존 항목의 이름을 그대로 반환해.
    2. 만약 완전히 새로운 직무라면, 범용적인 직무 카테고리 명칭(예: 마케팅, 개발, 디자인, 기획 등)으로 짧게 정제해서 반환해.
    3. 설명 없이 오직 '직무명' 단어 하나만 반환해.
    """

    return call_ai_common(
        prompt=prompt,
        status_msg="🛠️ AI가 직무를 분석하여 분류하고 있습니다...",
        output_type="text",
        fallback_value=input_job # 실패하면 입력값 그대로 사용
    )
