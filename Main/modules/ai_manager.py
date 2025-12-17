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
        return genai.GenerativeModel(MODEL_NAME, generation_config={"temperature": 0.7})
    except Exception as e:
        print(f"모델 설정 오류: {e}")
        return None

# ---------------------------------------------------------
# 🛠️ [503 오류 대응] 스마트 AI 호출 처리
# ---------------------------------------------------------
def call_ai_common(prompt, status_msg, output_type="text", fallback_value=None):
    model = configure_genai()
    if not model: return fallback_value

    max_retries = 1       # 최대 1번 재시도
    base_wait_time = 2    # 기본 대기 시간 2초

    with st.status(status_msg, expanded=False) as status:
        for attempt in range(max_retries + 1):
            try:
                # 시도 로그 출력 (터미널 확인용)
                print(f"📡 [AI 연결 시도] {attempt+1}회차...")
                
                response = model.generate_content(prompt)
                
                # 빈 응답 체크
                if not response.parts:
                    print("⚠️ [경고] 빈 응답 수신 (Safety Filter 등)")
                    return fallback_value
                
                text = response.text.strip()
                
                # 마크다운 제거 및 결과 반환 (성공 시 바로 탈출)
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

            # 🚨 503 Service Unavailable (서버 과부하/점검) 처리
            except exceptions.ServiceUnavailable:
                if attempt < max_retries:
                    # 점진적으로 대기 시간 늘리기 (2초 -> 4초)
                    sleep_time = base_wait_time * (2 ** attempt)
                    msg = f"🚧 구글 서버가 혼잡합니다(503). {sleep_time}초 후 다시 연결합니다... ({attempt+1}/{max_retries})"
                    print(f"🛑 [503 오류] {msg}")
                    status.update(label=msg, state="running")
                    time.sleep(sleep_time)
                else:
                    status.update(label="❌ 서버 응답 없음 (Google 503)", state="error")
                    st.error("📉 **Google AI 서버가 현재 응답하지 않습니다.** (503 Error)\n잠시 후 다시 시도해 주세요.")
                    return fallback_value

            # 429 Resource Exhausted (사용량 초과)
            except exceptions.ResourceExhausted:
                if attempt < max_retries:
                    msg = f"⏳ 사용량이 많아 대기 중... ({attempt+1}/{max_retries})"
                    status.update(label=msg, state="running")
                    time.sleep(base_wait_time)
                else:
                    status.update(label="❌ 사용량 초과 (재시도 실패)", state="error")
                    return fallback_value
            
            # 400 API Key 오류
            except exceptions.InvalidArgument:
                status.update(label="⛔ API 키 오류", state="error")
                if "USER_API_KEY" in st.session_state: del st.session_state["USER_API_KEY"]
                return fallback_value
                
            # 그 외 알 수 없는 오류
            except Exception as e:
                print(f"💥 [기타 에러] {e}")
                if attempt < max_retries:
                    time.sleep(1)
                else:
                    status.update(label="❌ 오류 발생", state="error")
                    return fallback_value

    return fallback_value

# ---------------------------------------------------------
# 2. 메인 AI 답변 생성
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
    
    * 주의: ⚡ 레시피: 이 후에 언급된 도구들은 무시해줘.
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