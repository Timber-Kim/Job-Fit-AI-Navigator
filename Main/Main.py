import streamlit as st
import google.generativeai as genai

# ==========================================
# 1. 설정 (여기에 API 키를 넣어주세요)
# ==========================================
# 실제 배포시에는 API 키를 코드에 직접 노출하면 안 되지만, 연습용이므로 여기에 적습니다.
GOOGLE_API_KEY = "AIzaSyB4becnPlwrNn9rUGCMV4yzRZ5qqWvcmiw"

genai.configure(api_key=GOOGLE_API_KEY)

# ==========================================
# 2. '젬(Gem)' 만들기 (시스템 프롬프트 설정)
# ==========================================
# 여기가 바로 젬을 만드는 핵심 부분입니다!
sys_instruction = """
직무별(ex. HR, Accounting, Marketing, Engineer, ML Engineer, Developer, Finance, FP&A 등등등)로 사용하기 좋은 AI를 추천해주는 챗봇/AI를 만들고싶어.
단, 직무별로, 어떠한 상황에서 사용하기 좋은 AI Tool을 추천해주는 챗봇이라서, 어떤 직무인지, 어떤 상황인지, 어떤 output을 만들고 싶은지를 고려해서 적절한 Tool을 추천해줘야해
그리고 output의 예시 화면도 보여주면 좋겠어
맨 처음에는 직무를 선택하게 하고, 그 다음엔 어떤 상황인지 구체적으로 받아(예시를 몇개 줘)
그리고 원하는 output tool을 선택하게 한 후 최종적으로 AI Tool을 추천해줘 (예시 화면도 같이)
혹시 처음에 기본값이 사용자가 입력하는게 먼저가 아니라, 네가 먼저 직무를 물어봐줄 수 있나?
"""

# AI 모델 불러오기 (gemini-1.5-flash 모델 사용 - 빠르고 저렴함)
model = genai.GenerativeModel(
    'gemini-2.5-pro',
    system_instruction=sys_instruction
)

# ==========================================
# 3. 웹 화면 구성 (Streamlit)
# ==========================================
st.title("🤖 AI 도구 추천 파트너")
st.markdown("직무와 상황을 입력하면, **Gemini AI**가 실시간으로 도구를 추천해줍니다.")

# 사용자 입력 받기
with st.form("request_form"):
    role = st.text_input("직무 (예: 마케터, 개발자, 학생)")
    situation = st.text_area("어떤 상황인가요? (예: 내일 발표할 PPT를 급하게 만들어야 해)")
    submit = st.form_submit_button("추천 받기")

# ==========================================
# 4. AI에게 질문하고 답변 받기
# ==========================================
if submit and role and situation:
    with st.spinner("AI가 적절한 도구를 찾고 있습니다..."):
        try:
            # AI에게 보낼 질문 조합
            user_prompt = f"나는 '{role}'이고, 현재 '{situation}' 상황이야. 나에게 맞는 AI 툴을 추천해줘."
            
            # AI 답변 생성
            response = model.generate_content(user_prompt)
            
            # 결과 출력
            st.success("추천이 완료되었습니다!")
            st.markdown(response.text)
            
        except Exception as e:
            st.error(f"에러가 발생했습니다: {e}")
            st.warning("API 키가 올바른지 확인해주세요.")