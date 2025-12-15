import streamlit as st
import google.generativeai as genai
import json
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

# [핵심 수정] 도구 정보 추출 (일반화 기능 강화)
def parse_tools(user_text, ai_text):
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        
        prompt = f"""
        Analyze the conversation below and extract the recommended AI tools into a JSON list.
        
        [Conversation]
        Q: {user_text}
        A: {ai_text}
        
        [IMPORTANT: Style Guide for Database Optimization]
        Please summarize the content into short, concise keywords like a database entry.
        
        1. **추천도구 (Tool Name):** Exact tool name only.
        2. **직무 (Job):** Standardized job title (e.g., '마케터', '개발자').
        
        3. **상황 (Situation):** - Do NOT just copy the user's specific request. 
           - Define the **General Core Capability** of the tool.
           - Example: User asks "Logo Design" -> You save "이미지 생성" (NOT "Logo Design").
           - Example: User asks "Python Debugging" -> You save "코드 작성 및 수정".
           - Max 15 chars. Use Noun phrases.
           
        4. **결과물 (Output):** Concrete noun. (e.g., "PPT 슬라이드", "소스 코드").
        5. **특징_및_팁 (Tips):** One short sentence summarizing the core benefit. Max 40 chars.
        6. **유료여부 (Price):** Only use "무료", "유료", "부분유료".
        7. **링크 (Link):** URL starting with http.

        Format: JSON List
        """
        
        res = model.generate_content(prompt)
        text = res.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text) if text.startswith("[") else [json.loads(text)]
    except:
        return []

# 직무 표준화 (기존 동일)
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