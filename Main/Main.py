import streamlit as st
import google.generativeai as genai
import pandas as pd
import os

# ==========================================
# 1. 기본 설정
# ==========================================
# 페이지 기본 설정 (탭 이름 등)
st.set_page_config(
    page_title="Job-Fit AI 도구 추천",
    page_icon="🤖",
    layout="wide"
)

# API 키 설정
try:
    # Streamlit Cloud 배포 시 Secrets 사용
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    # 내 컴퓨터에서 로컬 테스트 시 직접 입력
    GOOGLE_API_KEY = "여기에_API_키를_입력하세요"

genai.configure(api_key=GOOGLE_API_KEY)

# ==========================================
# 2. 데이터 로드 함수 (오류 방지 기능 추가)
# ==========================================
@st.cache_data
def load_data():
    file_path = 'ai_tools.csv'
    
    # 파일이 없으면 빈 데이터 반환
    if not os.path.exists(file_path):
        return None
    
    # 1차 시도: utf-8 인코딩 (일반적)
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
        return df
    except:
        # 2차 시도: cp949 인코딩 (한글 윈도우 & 엑셀 저장 시)
        # on_bad_lines='skip': 쉼표 개수가 안 맞는 오류 행은 무시하고 읽기
        try:
            df = pd.read_csv(file_path, encoding='cp949', on_bad_lines='skip')
            return df
        except:
            return None

# 데이터 불러오기
df_tools = load_data()

# ==========================================
# 3. 사이드바 (필터 및 설정)
# ==========================================
with st.sidebar:
    st.title("🎛️ 추천 옵션")
    
    # 요구사항: Output 템플릿 선택
    output_format = st.multiselect(
        "필요한 결과물 양식은?",
        ["보고서(텍스트)", "PPT(발표자료)", "이미지", "영상", "표(Excel)", "요약본"],
        default=[]
    )
    
    st.divider()
    
    # 데이터 로드 상태 표시
    if df_tools is not None:
        st.success(f"✅ AI 도구 데이터 연동됨 ({len(df_tools)}개)")
        with st.expander("데이터 미리보기"):
            st.dataframe(df_tools.head(3))
    else:
        st.error("❌ 'ai_tools.csv' 파일을 찾을 수 없습니다.")

    st.info("💡 팁: '만족도 보정'은 현재 세션에서만 유지됩니다.")
    if st.button("🗑️ 대화 내용 초기화"):
        st.session_state.messages = []
        st.rerun()

# ==========================================
# 4. AI 설정 (시스템 프롬프트 최적화)
# ==========================================
# CSV 데이터를 텍스트로 변환
csv_context = ""
if df_tools is not None:
    csv_context = f"""
    [내부 AI 도구 데이터베이스]
    {df_tools.to_string(index=False)}
    """

# 프롬프트: 사용자의 요청을 반영하여 말투와 형식을 지정
sys_instruction = f"""
너는 '직무/상황별 AI 도구 추천 전문가'야. 
사용자의 직무와 상황을 듣고, [내부 AI 도구 데이터베이스]를 최우선으로 참고하여 도구를 추천해줘.

### 🎯 답변 원칙:
1. **데이터 우선:** 데이터베이스에 있는 도구라면, 그 내용을 바탕으로 설명해. (데이터베이스에 없으면 외부 지식 활용)
2. **형식 준수:** 줄글로 길게 쓰지 말고, **'표(Table)'** 또는 **'글머리 기호'**를 써서 핵심만 딱딱 짚어줘.
3. **사용자 필터:** 사용자가 {', '.join(output_format) if output_format else '특정 양식'}을 원한다면 그에 맞는 툴을 우선 추천해.
4. **필수 포함 정보:**
   - 도구명 (유료/무료 여부)
   - 추천 이유 (상황에 빗대어 1줄 요약)
   - 주요 특징
   - 바로가기 링크 (URL)

###  말투 예시:
- "마케터시군요! 카드뉴스 제작에는 이 툴이 딱입니다."
- (설명은 명사형으로 간결하게 끝맺음)

{csv_context}
"""

# Gemini 2.5 Pro 사용
model = genai.GenerativeModel(
    'gemini-2.5-pro',
    system_instruction=sys_instruction
)

# ==========================================
# 5. 메인 채팅 인터페이스
# ==========================================
st.title("🚀 Job-Fit AI 네비게이터")
st.caption("당신의 업무 상황을 말해주세요. 최적의 AI 도구를 찾아드립니다.")

# 대화 기록 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 기존 대화 내용 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 채팅 입력창
if prompt := st.chat_input("예: 개발자인데 코드짜는 거 도와주는 무료 툴 있어?"):
    
    # 사용자 메시지 표시
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # AI 답변 생성
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        try:
            # 대화 기록(Context) 구성
            chat_history = [
                {"role": m["role"], "parts": [m["content"]]} 
                for m in st.session_state.messages 
                if m["role"] != "system" # 시스템 메시지 제외
            ]
            
            # AI에게 질문
            chat = model.start_chat(history=chat_history)
            response = chat.send_message(prompt)
            
            # 답변 출력
            message_placeholder.markdown(response.text)
            
            # 답변 저장
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            
            # 만족도 피드백 UI (기능 흉내)
            col1, col2, col3 = st.columns([1, 1, 8])
            with col1:
                st.button("👍 도움됨", key=f"up_{len(st.session_state.messages)}")
            with col2:
                st.button("👎 별로임", key=f"down_{len(st.session_state.messages)}")

        except Exception as e:
            message_placeholder.error("죄송합니다. 잠시 오류가 발생했습니다.")
            st.error(f"상세 에러: {e}")