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
        # 로컬에서 실행 중이라 secrets가 없다면 예외 처리가 필요할 수 있습니다.
        if "GOOGLE_API_KEY" in st.secrets:
            genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        else:
            # secrets가 없을 경우를 대비해 직접 입력하거나 환경변수 사용 가능
            # (여기서는 일단 None 반환)
            return None
            
        return genai.GenerativeModel(MODEL_NAME, generation_config={"temperature": 0.8})
    except Exception as e:
        print(f"모델 설정 오류: {e}")
        return None

# ---------------------------------------------------------
# 2. AI 답변 생성 (핵심 수정됨)
# ---------------------------------------------------------
def get_ai_response(messages, df_tools):
    model = configure_genai()
    if not model: 
        # API 키가 없으면 에러를 발생시켜 main.py가 알게 하거나 메시지 반환
        return "⚠️ API Key 설정 오류: secrets.toml 파일을 확인해주세요."

    csv_context = ""
    if not df_tools.empty:
        # [핵심 변경] AI가 인기도를 판단해야 하므로 '추천수'는 보여줍니다!
        # '비추천수'만 숨깁니다. (부정적 편향 방지)
        display_cols = [c for c in df_tools.columns if c != '비추천수']
        csv_context = df_tools[display_cols].to_string(index=False)
    
    # 시스템 프롬프트 포맷팅
    full_prompt = SYSTEM_PROMPT_TEMPLATE.format(csv_context=csv_context)
    
    # 모델에 시스템 지침 설정 (GenerativeModel 생성 시점에 넣는 것이 권장됨)
    model = genai.GenerativeModel(MODEL_NAME, system_instruction=full_prompt)

    # 대화 기록 변환
    history = [
        {"role": "user" if m["role"]=="user" else "model", "parts": [m["content"]]} 
        for m in messages[:-1]
    ]
    
    # ⚠️ [중요] 여기서 try-except를 제거했습니다!
    # 에러가 발생하면 main.py의 'get_ai_response_safe' 함수가 잡아서 
    # '30초 대기' 로직을 실행합니다.
    chat = model.start_chat(history=history)
    response = chat.send_message(messages[-1]["content"]) # 혹은 generate_content 사용
    
    return response.text

# ---------------------------------------------------------
# 3. 도구 정보 추출 (AI 기반)
# ---------------------------------------------------------
def parse_tools(user_query, ai_response_text):
    """
    AI 답변 텍스트에서 추천된 도구 이름만 추출합니다.
    """
    model = configure_genai() # 모델 객체 새로 생성
    if not model: return []

    try:
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

        extraction_response = model.generate_content(extraction_prompt)
        text = extraction_response.text.strip()

        # 마크다운 제거
        text = text.replace("```json", "").replace("```", "").strip()
        
        # JSON 파싱
        tool_names = json.loads(text)
        
        if isinstance(tool_names, list):
            # 메인 코드 형식에 맞게 변환
            return [{"추천도구": name} for name in tool_names if isinstance(name, str)]
            
        return []

    except Exception as e:
        # 파싱 에러는 프로그램 중단을 막기 위해 로그만 남기고 빈 리스트 반환
        print(f"Tool Extraction Error: {e}")
        return []

# ---------------------------------------------------------
# 4. 직무 분류/표준화 (관리자용)
# ---------------------------------------------------------
def categorize_jobs_with_ai(job_list):
    """
    main.py에서 관리자 메뉴가 호출하는 함수
    """
    model = configure_genai()
    if not model: return {}

    try:
        prompt = f"""
        다음 직무 목록을 분석하여 의미가 같거나 매우 유사한 직무들을 하나로 묶어주세요.
        가장 보편적인 직무명을 Key로, 묶일 직무들의 리스트를 Value로 하는 JSON을 만드세요.
        변경이 필요 없는 직무는 포함하지 마세요.

        [직무 목록]
        {job_list}

        [출력 예시]
        {{"마케터": ["마케팅", "퍼포먼스 마케터"], "개발자": ["프론트엔드 개발", "백엔드"]}}
        
        오직 JSON만 출력하세요.
        """
        resp = model.generate_content(prompt)
        text = resp.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except:
        return {}