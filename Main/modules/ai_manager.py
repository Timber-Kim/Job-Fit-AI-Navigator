import streamlit as st
import google.generativeai as genai
import json
import re
from .config import SYSTEM_PROMPT_TEMPLATE, MODEL_NAME

# 제미나이 설정
def configure_genai():
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        return genai.GenerativeModel(MODEL_NAME, generation_config={"temperature": 0.8})
    except:
        return None

# AI 답변 생성
def get_ai_response(messages, df_tools):
    model = configure_genai()
    if not model: return "API Key 오류"

    csv_context = ""
    if not df_tools.empty:
        # [핵심 변경] AI가 인기도를 판단해야 하므로 '추천수'는 보여줍니다!
        # '비추천수'만 숨깁니다. (부정적 편향 방지)
        display_cols = [c for c in df_tools.columns if c != '비추천수']
        csv_context = df_tools[display_cols].to_string(index=False)
    
    full_prompt = SYSTEM_PROMPT_TEMPLATE.format(csv_context=csv_context)
    model = genai.GenerativeModel(MODEL_NAME, system_instruction=full_prompt)

    history = [{"role": "user" if m["role"]=="user" else "model", "parts": [m["content"]]} 
               for m in messages[:-1]]
    
    try:
        chat = model.start_chat(history=history)
        response = chat.send_message(messages[-1]["content"])
        return response.text
    except Exception as e:
        return f"오류: {e}"

# 도구 정보 추출 (이전과 동일)
def parse_tools(user_query, ai_response_text):
    """
    AI 답변 텍스트에서 추천된 도구 이름만 'AI를 이용해' 스마트하게 추출합니다.
    """
    try:
        # 추출 전용 프롬프트
        extraction_prompt = f"""
        다음은 AI가 사용자에게 답변한 내용입니다.
        이 답변 내용 중에서 추천된 'AI 도구 이름' 또는 '소프트웨어 서비스 이름'만 추출하세요.
        
        [답변 내용]
        {ai_response_text}
        
        [규칙]
        1. 결과는 반드시 순수한 JSON 리스트 포맷이어야 합니다. (예: ["ChatGPT", "Midjourney", "Gamma"])
        2. 도구 이름이 명확하지 않으면 빈 리스트 [] 를 반환하세요.
        3. 부연 설명 없이 JSON만 출력하세요.
        """

        # 모델 설정이 모듈 내에 없다면 여기서 잠시 초기화 (이미 있다면 생략 가능)
        # genai.configure(api_key="YOUR_API_KEY") 
        # model = genai.GenerativeModel('gemini-2.5-flash')
        
        # AI에게 추출 요청
        extraction_response = model.generate_content(extraction_prompt)
        text = extraction_response.text.strip()

        # 혹시 모를 마크다운 제거 (```json ... ```)
        text = text.replace("```json", "").replace("```", "").strip()
        
        # JSON 변환
        tool_names = json.loads(text)
        
        # 리스트가 아니거나 비어있으면 빈 리스트 반환
        if not isinstance(tool_names, list):
            return []
            
        # 메인 코드 형식에 맞게 변환 ([{'추천도구': '이름'}] 형식)
        parsed_tools = [{"추천도구": name} for name in tool_names if isinstance(name, str)]
        
        return parsed_tools

    except Exception as e:
        print(f"Tool Extraction Error: {e}")
        return []

# 직무 표준화 (이전과 동일)
def normalize_job_category(new_job, existing_jobs):
    if not existing_jobs: return new_job
    model = configure_genai()
    if not model: return new_job

    prompt = f"""
    새로운 직무: "{new_job}"
    기존 직무 목록: {existing_jobs}
    
    1. '새로운 직무'가 '기존 직무 목록' 중 하나와 의미가 같다면, 그 **기존 직무명**을 반환해.
    2. 완전히 새로운 직무라면, "{new_job}" 그대로 반환해.
    3. 오직 단어 하나만 출력해.
    """
    try:
        res = model.generate_content(prompt)
        return res.text.strip()
    except:
        return new_job