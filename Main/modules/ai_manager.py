import streamlit as st
import google.generativeai as genai
import json
import re
from .config import SYSTEM_PROMPT_TEMPLATE, MODEL_NAME

# ---------------------------------------------------------
# 1. 제미나이 설정 (공통 사용)
# ---------------------------------------------------------
def configure_genai():
    try:
        # Streamlit Secrets에서 API 키를 가져옵니다.
        if "GOOGLE_API_KEY" in st.secrets:
            genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        else:
            return None
            
        return genai.GenerativeModel(MODEL_NAME, generation_config={"temperature": 0.8})
    except Exception as e:
        print(f"모델 설정 오류: {e}")
        return None

# ---------------------------------------------------------
# 2. AI 답변 생성 (에러는 main.py로 전달)
# ---------------------------------------------------------
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
# 3. 도구 정보 추출 (AI 기반)
# ---------------------------------------------------------
def parse_tools(user_query, ai_response_text):
    model = configure_genai()
    if not model: return []

    try:
        extraction_prompt = f"""
        다음은 AI가 사용자에게 답변한 내용입니다.
        이 답변 내용 중에서 추천된 'AI 도구 이름' 또는 '소프트웨어 서비스 이름'만 추출하세요.
        
        [답변 내용]
        {ai_response_text}
        
        [규칙]
        1. 결과는 반드시 순수한 JSON 리스트 포맷이어야 합니다. (예: ["ChatGPT", "Midjourney"])
        2. 도구 이름이 명확하지 않으면 빈 리스트 [] 를 반환하세요.
        3. 부연 설명 없이 JSON만 출력하세요.
        """

        extraction_response = model.generate_content(extraction_prompt)
        text = extraction_response.text.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        
        tool_names = json.loads(text)
        
        if isinstance(tool_names, list):
            return [{"추천도구": name} for name in tool_names if isinstance(name, str)]
            
        return []

    except Exception as e:
        print(f"Tool Extraction Error: {e}")
        return []

# ---------------------------------------------------------
# 4. 직무 표준화 (누락되었던 함수 추가됨 ✅)
# ---------------------------------------------------------
def normalize_job_category(new_job, existing_jobs):
    """
    새로운 직무 입력 시 기존 DB에 있는 유사 직무로 매핑해주는 함수
    """
    if not existing_jobs: return new_job
    
    model = configure_genai()
    if not model: return new_job

    prompt = f"""
    새로운 직무: "{new_job}"
    기존 직무 목록: {existing_jobs}
    
    1. '새로운 직무'가 '기존 직무 목록' 중 하나와 의미가 완벽히 같다면, 그 **기존 직무명**을 반환해.
    2. 완전히 새로운 직무라면, "{new_job}" 그대로 반환해.
    3. 오직 단어 하나만 출력해. (설명 금지)
    """
    try:
        res = model.generate_content(prompt)
        return res.text.strip()
    except:
        # 에러 발생 시 그냥 원래 입력값 사용
        return new_job

# ---------------------------------------------------------
# 5. 직무 분류 (관리자용)
# ---------------------------------------------------------
def categorize_jobs_with_ai(job_list):
    model = configure_genai()
    if not model: return {}

    try:
        prompt = f"""
        다음 직무 목록을 분석하여 의미가 같거나 매우 유사한 직무들을 하나로 묶어주세요.
        가장 보편적인 직무명을 Key로, 묶일 직무들의 리스트를 Value로 하는 JSON을 만드세요.
        
        [직무 목록]
        {job_list}
        
        오직 JSON만 출력하세요.
        """
        resp = model.generate_content(prompt)
        text = resp.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except:
        return {}