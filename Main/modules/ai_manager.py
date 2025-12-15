import streamlit as st
import google.generativeai as genai
from google.api_core import exceptions
import time
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
def normalize_job_category(input_job, existing_jobs):
    """
    입력된 직무를 기존 직무 리스트 중 하나로 표준화하거나 새로운 직무명을 제안합니다.
    (429 오류 발생 시 대기 및 재시도 로직 포함)
    """
    
    # AI에게 보낼 프롬프트 구성
    jobs_str = ", ".join(existing_jobs)
    prompt = f"""
    사용자가 입력한 직무: '{input_job}'
    
    현재 우리 DB에 있는 직무 목록: [{jobs_str}]
    
    [지시사항]
    1. 사용자의 입력이 기존 목록의 항목과 의미상 매우 유사하다면, 그 기존 항목의 이름을 그대로 반환해.
    2. 만약 완전히 새로운 직무라면, 범용적인 직무 카테고리 명칭(예: 마케팅, 개발, 디자인, 기획 등)으로 짧게 정제해서 반환해.
    3. 설명 없이 오직 '직무명' 단어 하나만 반환해.
    """

    # === [여기가 핵심 수정: 재시도 로직 추가] ===
    max_retries = 3
    wait_time = 30

    # 상태바 표시 (Main.py와 동일한 스타일)
    with st.status("🛠️ AI가 직무를 분석하여 분류하고 있습니다...", expanded=False) as status:
        for attempt in range(max_retries):
            try:
                # AI 호출 (generate_content는 기존에 쓰시던 변수명에 맞게 조정 필요)
                # 가정: model = genai.GenerativeModel(...) 이 선언되어 있다고 가정
                response = model.generate_content(prompt)
                result = response.text.strip()
                
                # 성공 시 상태 업데이트
                status.update(label=f"✅ 분류 완료: {result}", state="complete", expanded=False)
                return result

            except exceptions.ResourceExhausted:
                # 사용량 초과 시 대기
                msg = f"⏳ 사용량이 많아 잠시 대기 중입니다... ({attempt + 1}/{max_retries})"
                status.update(label=msg, state="running")
                time.sleep(wait_time) # 대기

            except Exception as e:
                # 그 외 오류 발생 시 -> 그냥 입력값 그대로 사용 (Fallback)
                print(f"직무 표준화 오류: {e}")
                status.update(label="⚠️ 분류 실패 (입력값 그대로 사용)", state="error")
                return input_job

    # 재시도 횟수 초과 시 -> 입력값 그대로 반환 (저장은 되어야 하니까요)
    return input_job

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