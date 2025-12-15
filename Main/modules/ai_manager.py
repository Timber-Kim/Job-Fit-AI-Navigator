import streamlit as st
import google.generativeai as genai
import json
from .config import SYSTEM_PROMPT_TEMPLATE, MODEL_NAME

# 제미나이 설정 (모델명 변수 사용)
def configure_genai():
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        # 요청하신 gemini-2.5-flash 사용
        return genai.GenerativeModel(MODEL_NAME, generation_config={"temperature": 0.8})
    except:
        return None

# AI 답변 생성
def get_ai_response(messages, df_tools):
    model = configure_genai()
    if not model: return "API Key 오류"

    csv_context = ""
    if not df_tools.empty:
        # 추천수/비추천수는 편향 방지를 위해 AI에게는 숨김
        display_cols = [c for c in df_tools.columns if c not in ['비추천수', '추천수']]
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

# 도구 정보 추출
def parse_tools(user_text, ai_text):
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        prompt = f"""
        Extract recommended AI tools from the conversation below into a JSON list.
        Q: {user_text} / A: {ai_text}
        Format: [{{"추천도구": "Name", "직무": "Job", "상황": "Situation", "결과물": "Output", "특징_및_팁": "Tips", "유료여부": "Price", "링크": "URL"}}]
        Only JSON.
        """
        res = model.generate_content(prompt)
        text = res.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text) if text.startswith("[") else [json.loads(text)]
    except:
        return []

# [신규] 저장 시점 자동 직무 표준화
def normalize_job_category(new_job, existing_jobs):
    """
    새로운 직무(new_job)가 들어왔을 때, 기존 직무 리스트(existing_jobs) 중
    어디에 속하는지 AI가 판단하여 표준화된 이름을 반환.
    """
    if not existing_jobs: return new_job
    
    model = configure_genai()
    if not model: return new_job

    prompt = f"""
    새로운 직무: "{new_job}"
    기존 직무 목록: {existing_jobs}
    
    [지시사항]
    1. '새로운 직무'가 '기존 직무 목록' 중 하나와 의미가 같다면, 그 **기존 직무명**을 반환해.
       (예: '백엔드 코딩' -> 목록에 '개발자'가 있다면 '개발자' 반환)
    2. 완전히 새로운 직무라면, "{new_job}" 그대로 반환해.
    3. 오직 **직무명 단어 하나만** 출력해. (설명 금지)
    """
    try:
        res = model.generate_content(prompt)
        return res.text.strip()
    except:
        return new_job