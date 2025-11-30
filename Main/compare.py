import streamlit as st
import google.generativeai as genai
import pandas as pd
import os

# ==========================================
# (추가 기능) CSV에 데이터 추가하는 함수
# ==========================================
def save_to_csv(new_data):
    file_path = 'ai_tools.csv'
    try:
        # 기존 데이터 불러오기
        df = pd.read_csv(file_path, encoding='utf-8-sig', on_bad_lines='skip')
        
        # 새로운 데이터프레임 생성
        new_row = pd.DataFrame([new_data])
        
        # 합치기 (concat 사용)
        df_updated = pd.concat([df, new_row], ignore_index=True)
        
        # 다시 저장 (utf-8-sig로 저장해야 엑셀에서 안 깨짐)
        df_updated.to_csv(file_path, index=False, encoding='utf-8-sig')
        return True
    except Exception as e:
        st.error(f"저장 중 오류 발생: {e}")
        return False

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
# 2. 데이터 로드 함수 (최종 수정: 파싱 에러 무시 기능 추가)
# ==========================================
@st.cache_data
def load_data():
    target_file = 'ai_tools.csv'
    found_path = None

    # 1. 파일 찾기 (탐정 모드 유지)
    for root, dirs, files in os.walk(os.getcwd()):
        if target_file in files:
            found_path = os.path.join(root, target_file)
            break
            
    if found_path is None:
        # 못 찾았을 경우 상위 폴더 검색
        parent_dir = os.path.dirname(os.getcwd())
        for root, dirs, files in os.walk(parent_dir):
            if target_file in files:
                found_path = os.path.join(root, target_file)
                break

    if found_path is None:
        st.error("🚨 파일을 찾을 수 없습니다.")
        return None
        
    # 2. 파일 읽기 (여기가 중요! UTF-8에도 on_bad_lines 옵션 추가)
    try:
        # 옵션 설명: 
        # encoding='utf-8-sig': 엑셀로 저장한 CSV의 깨짐 방지 (BOM 처리)
        # on_bad_lines='skip': 칸 수가 안 맞는 불량 행은 쿨하게 패스
        df = pd.read_csv(found_path, encoding='utf-8-sig', on_bad_lines='skip')
        return df
    except Exception as e_utf8:
        # 혹시 UTF-8이 아니라고 할까봐 CP949도 대비
        try:
            df = pd.read_csv(found_path, encoding='cp949', on_bad_lines='skip')
            return df
        except Exception as e_final:
            st.error(f"❌ 읽기 실패. 파일 내용이나 인코딩을 확인해주세요.")
            st.error(f"상세 에러: {e_final}")
            return None

# 데이터 불러오기
df_tools = load_data()

# ==========================================
# 3. 사이드바 (데이터 기반 필터링)
# ==========================================
with st.sidebar:
    st.title("🎛️ 추천 옵션")
    
    # [새로운 기능] CSV 기반 직무/상황 선택 기능
    selected_job = "직접 입력"
    selected_situation = "직접 입력"
    
    if df_tools is not None:
        # 1. 직무 목록 추출 (중복 제거 및 정렬)
        job_list = sorted(df_tools['직무'].unique().tolist())
        # '직접 입력' 옵션을 맨 앞에 추가
        selected_job = st.selectbox("직무를 선택하세요", ["직접 입력"] + job_list)
        
        # 2. 선택한 직무에 맞는 상황 목록만 필터링
        if selected_job != "직접 입력":
            # 해당 직무의 상황 데이터만 가져오기
            situation_list = sorted(df_tools[df_tools['직무'] == selected_job]['상황'].unique().tolist())
            selected_situation = st.selectbox("어떤 상황인가요?", ["직접 입력"] + situation_list)
    # 결과물 양식 선택 (기존 유지)
    output_format = st.multiselect(
        "필요한 결과물 양식",
        ["보고서(텍스트)", "PPT(발표자료)", "이미지", "영상", "표(Excel)", "요약본"],
        default=[]
    )

    st.divider()
        
    
    st.info("💡 팁: 직무와 상황을 선택하고 '자동 질문 생성' 버튼을 누르면 편합니다.")
    
    # 대화 초기화 버튼
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
    'gemini-2.5-Pro',
    system_instruction=sys_instruction
)

# ==========================================
# 5. 메인 채팅 인터페이스 (버튼 & 채팅 통합 버전)
# ==========================================
st.title("🚀 Job-Fit AI 네비게이터")
st.caption("당신의 업무 상황을 말해주세요. 최적의 AI 도구를 찾아드립니다.")

# 대화 기록 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# -------------------------------------------------------
# 1. 기존 대화 내용 표시
# -------------------------------------------------------
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# -------------------------------------------------------
# 2. 버튼으로 질문하기 (사이드바 연동)
# -------------------------------------------------------
# 사이드바에서 선택된 값이 있고, 아직 질문하지 않은 상태일 때만 버튼 동작
if selected_job != "직접 입력" and selected_situation != "직접 입력":
    # 버튼 문구 생성
    btn_label = f"🔍 '{selected_job}' - '{selected_situation}' 추천받기"
    
    if st.button(btn_label, type="primary"):
        # 자동 질문 생성
        auto_prompt = f"나는 '{selected_job}' 직무를 맡고 있어. 현재 '{selected_situation}' 업무를 해야 하는데 적합한 AI 도구를 추천해줘."
        
        # 메시지 저장 및 화면 새로고침 (중요!)
        st.session_state.messages.append({"role": "user", "content": auto_prompt})
        st.rerun()

# -------------------------------------------------------
# 3. 채팅창으로 직접 질문하기
# -------------------------------------------------------
if prompt := st.chat_input("직접 질문하기 (예: 무료로 쓸 수 있는 PPT 도구 있어?)"):
    # 메시지 저장 및 화면 새로고침
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

# ==========================================
# 4. AI 답변 생성 및 피드백 저장 로직
# ==========================================
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        try:
            with st.spinner("AI가 생각 중입니다..."):
                # 대화 맥락 구성
                chat_history = [
                    {"role": m["role"], "parts": [m["content"]]} 
                    for m in st.session_state.messages 
                    if m["role"] != "system"
                ]
                
                # AI 답변 요청
                chat = model.start_chat(history=chat_history[:-1])
                response = chat.send_message(st.session_state.messages[-1]["content"])
                
                # 답변 출력 및 저장
                message_placeholder.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
        
        except Exception as e:
            message_placeholder.error("오류가 발생했습니다.")
            st.error(e)

# -------------------------------------------------------
# [업그레이드] 답변별 '데이터 추가' 기능 (대화 루프 밖에서 처리)
# -------------------------------------------------------
# 가장 최근 답변이 AI인 경우에만 추천 저장 버튼 표시
if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
    
    st.divider()
    st.caption("이 답변이 마음에 드시나요? 데이터베이스에 추가해보세요!")
    
    # Expander로 저장 양식 열기
    with st.expander("💾 이 추천을 CSV에 저장하기 (Click)"):
        with st.form("save_tool_form"):
            st.write("아래 내용을 확인하고 저장 버튼을 눌러주세요.")
            
            # 사용자 질문과 AI 답변을 미리 채워넣기 위한 변수
            last_user_msg = st.session_state.messages[-2]["content"] if len(st.session_state.messages) > 1 else ""
            last_ai_msg = st.session_state.messages[-1]["content"]
            
            # CSV 컬럼에 맞게 입력창 만들기
            col1, col2 = st.columns(2)
            with col1:
                input_job = st.text_input("직무", value="사용자추천")
                input_situation = st.text_input("상황", value=last_user_msg[:30]+"...") # 질문 내용 일부 자동 입력
            with col2:
                input_output = st.text_input("결과물", value="기타")
                input_price = st.selectbox("유료여부", ["무료", "유료", "부분유료"])

            input_tool = st.text_input("추천 도구 이름", placeholder="예: ChatGPT")
            input_desc = st.text_area("특징 및 팁", value=last_ai_msg[:100]+"...") # AI 답변 일부 자동 입력
            input_link = st.text_input("링크 (URL)", value="https://")
            
            # 저장 버튼
            submit_save = st.form_submit_button("✅ CSV에 저장하기")
            
            if submit_save:
                # 저장할 데이터 딕셔너리 생성
                new_data = {
                    "직무": input_job,
                    "상황": input_situation,
                    "결과물": input_output,
                    "추천도구": input_tool,
                    "특징_및_팁": input_desc,
                    "유료여부": input_price,
                    "링크": input_link
                }
                
                # 저장 함수 실행
                if save_to_csv(new_data):
                    st.success(f"'{input_tool}' 정보가 성공적으로 저장되었습니다! (새로고침 후 반영)")
                    # 캐시 데이터 비우기 (그래야 바로 반영됨)
                    st.cache_data.clear()
                else:
                    st.error("데이터 저장 중 오류가 발생했습니다.")

                    # ==========================================
# 3. 사이드바 (UI)
# ==========================================
with st.sidebar:
    st.title("🎛️ 추천 옵션")
    
    selected_job = "직접 입력"
    selected_situation = "직접 입력"
    
    if df_tools is not None:
        # 데이터 연동 확인 표시
        st.success(f"✅ DB 연동됨 ({len(df_tools)}개 도구)")
        
        job_list = sorted(df_tools['직무'].unique().tolist())
        selected_job = st.selectbox("직무를 선택하세요", ["직접 입력"] + job_list)
        
        if selected_job != "직접 입력":
            situation_list = sorted(df_tools[df_tools['직무'] == selected_job]['상황'].unique().tolist())
            selected_situation = st.selectbox("어떤 상황인가요?", ["직접 입력"] + situation_list)
    else:
        st.error("CSV 파일을 찾지 못했습니다.")
    
    st.divider()
    
    output_format = st.multiselect(
        "필요한 결과물 양식",
        ["보고서(텍스트)", "PPT(발표자료)", "이미지", "영상", "표(Excel)", "요약본"],
        default=[]
    )
    
    if st.button("🗑️ 대화 내용 초기화"):
        st.session_state.messages = []
        st.rerun()