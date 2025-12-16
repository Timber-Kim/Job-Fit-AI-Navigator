import streamlit as st
import google.generativeai as genai
from google.api_core import exceptions
import time
import json
import difflib
from .config import SYSTEM_PROMPT_TEMPLATE, MODEL_NAME

# ---------------------------------------------------------
# 1. 제미나이 설정 (공통 사용)
# ---------------------------------------------------------
def configure_genai():
    try:
        api_key = None
        user_key_input = st.session_state.get("USER_API_KEY", "").strip()
        
        if user_key_input:
            api_key = user_key_input
        elif "GOOGLE_API_KEY" in st.secrets:
            api_key = st.secrets["GOOGLE_API_KEY"]
        
        if not api_key: return None

        genai.configure(api_key=api_key)
        return genai.GenerativeModel(MODEL_NAME, generation_config={"temperature": 0.7}) # 온도를 낮춰서 정확도 향상
        
    except Exception as e:
        print(f"모델 설정 오류: {e}")
        return None

# ---------------------------------------------------------
# 🛠️ AI 호출 공통 처리 (유료 플랜 최적화: 재시도 최소화)
# ---------------------------------------------------------
def call_ai_common(prompt, status_msg, output_type="text", fallback_value=None):
    model = configure_genai()
    if not model: return fallback_value

    max_retries = 1      # 유료 플랜은 1번만 재시도해도 충분
    wait_time = 2        # 대기 시간 단축

    with st.status(status_msg, expanded=False) as status:
        for attempt in range(max_retries + 1):
            try:
                response = model.generate_content(prompt)
                if not response.parts:
                    return fallback_value
                
                text = response.text.strip()
                if "```" in text:
                    text = text.replace("```json", "").replace("```", "")

                if output_type == "json":
                    try:
                        result = json.loads(text)
                        if isinstance(fallback_value, list) and isinstance(result, dict):
                            result = [result]
                        status.update(label="✅ 처리 완료!", state="complete", expanded=False)
                        return result
                    except json.JSONDecodeError:
                        status.update(label="⚠️ 데이터 형식 오류", state="error")
                        return fallback_value
                else:
                    status.update(label="✅ 처리 완료!", state="complete", expanded=False)
                    return text

            except exceptions.InvalidArgument:
                status.update(label="⛔ API 키 오류!", state="error")
                if "USER_API_KEY" in st.session_state: del st.session_state["USER_API_KEY"]
                return fallback_value
            except Exception:
                time.sleep(1)

    status.update(label="❌ 응답 실패", state="error")
    return fallback_value

# ---------------------------------------------------------
# 2. 메인 AI 답변 생성 (데이터 다이어트 적용)
# ---------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=3600)
def get_ai_response(messages, df_tools):
    model = configure_genai()
    if not model: return "⚠️ API Key 설정 오류"

    csv_context = ""
    if not df_tools.empty:
        # 핵심 컬럼만 선별하여 토큰 절약
        essential_cols = ['추천도구', '직무', '상황', '특징_및_팁', '추천수', '비추천수', '링크']
        target_cols = [c for c in essential_cols if c in df_tools.columns]
        csv_context = df_tools[target_cols].to_string(index=False)
    
    full_prompt = SYSTEM_PROMPT_TEMPLATE.format(csv_context=csv_context)
    model = genai.GenerativeModel(MODEL_NAME, system_instruction=full_prompt)

    history = [{"role": "user" if m["role"]=="user" else "model", "parts": [m["content"]]} for m in messages[:-1]]
    
    try:
        chat = model.start_chat(history=history)
        response = chat.send_message(messages[-1]["content"])
        return response.text
    except Exception as e:
        return f"❌ 오류 발생: {str(e)}"

# ---------------------------------------------------------
# 3. 도구 정보 추출
# ---------------------------------------------------------
def parse_tools(user_question, ai_answer):
    # 답변 포맷(> ### [섹션] 도구명)에 맞춰 추출 프롬프트 최적화
    prompt = f"""
    [지시사항]
    아래 'AI 답변' 텍스트를 분석하여 추천된 도구 정보를 JSON 리스트로 추출해.
    
    **중요:** AI 답변은 `> ### [섹션명] 도구명` 형식으로 작성되어 있음. 이 패턴을 인식해서 추출해.
    
    [입력 데이터]
    - 사용자 질문: {user_question}
    - AI 답변: {ai_answer}
    
    [추출 목표 JSON 형식]
    [
      {{
        "추천도구": "도구명 (헤더에서 추출)",
        "직무": "사용자 질문에서 유추한 직무",
        "상황": "사용자 질문에서 유추한 상황",
        "결과물": "예상되는 결과물 (없으면 공란)",
        "특징_및_팁": "답변 내용 중 '활용법'이나 '팁' 내용 요약",
        "유료여부": "답변 내용 중 '가격' 정보 (없으면 공란)",
        "링크": "답변 내용 중 URL (없으면 공란)"
      }}
    ]
    
    * 주의: 워크플로우 레시피에 언급된 도구들도 포함해서 추출해줘.
    * 오직 JSON 데이터만 출력해. (마크다운 없이)
    """

    return call_ai_common(
        prompt=prompt,
        status_msg="⚡ 도구 정보를 추출하고 있습니다...", # 메시지 변경
        output_type="json",
        fallback_value=[]
    )

# ---------------------------------------------------------
# 4. 직무 표준화 (difflib)
# ---------------------------------------------------------
def normalize_job_category(input_job, existing_jobs):
    input_job = input_job.strip()
    if input_job in existing_jobs: return input_job
    matches = difflib.get_close_matches(input_job, existing_jobs, n=1, cutoff=0.6)
    return matches[0] if matches else input_job