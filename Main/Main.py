import streamlit as st
import google.generativeai as genai
import pandas as pd
import os
import json

# ==========================================
# 1. 기본 설정 및 데이터 로드
# ==========================================
st.set_page_config(page_title="Job-Fit AI 도구 추천",
                   page_icon="🤖",
                   layout="wide")

try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    GOOGLE_API_KEY = "여기에_API_키를_입력하세요" 

genai.configure(api_key=GOOGLE_API_KEY)

# 절대 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
CSV_FILE_PATH = os.path.join(current_dir, 'ai_tools.csv')

# 데이터 로드 함수
@st.cache_data
def load_data():
    if not os.path.exists(CSV_FILE_PATH):
        return None

    try:
        df = pd.read_csv(CSV_FILE_PATH, encoding='utf-8-sig', on_bad_lines='skip')
    except:
        try:
            df = pd.read_csv(CSV_FILE_PATH, encoding='cp949', on_bad_lines='skip')
        except:
            return None

    if df is not None:
        if '비추천수' not in df.columns:
            df['비추천수'] = 0
            df.to_csv(CSV_FILE_PATH, index=False, encoding='utf-8-sig')
            
    return df

df_tools = load_data()

# ==========================================
# 2. 도구 정보 추출 및 CSV 업데이트 로직
# ==========================================
def parse_tools_from_text(user_text, ai_text):
    """
    AI 답변에서 도구 목록을 추출하여 리스트로 반환 (버튼 생성용)
    """
    try:
        extractor_model = genai.GenerativeModel('gemini-2.5-flash')
        
        extraction_prompt = f"""
        아래 대화에서 AI가 추천한 **AI 도구 이름**들을 모두 찾아서 JSON 리스트로 줘.
        
        [대화]
        Q: {user_text}
        A: {ai_text}
        
        [요청사항]
        1. 도구 이름, 직무, 상황, 결과물, 특징_및_팁, 유료여부, 링크를 추출해.
        2. 직무/상황 등은 질문과 답변을 보고 추론해.
        
        출력 포맷(JSON List):
        [
            {{
                "추천도구": "도구명",
                "직무": "...",
                "상황": "...",
                "결과물": "...",
                "특징_및_팁": "...",
                "유료여부": "...",
                "링크": "..."
            }}
        ]
        """
        result = extractor_model.generate_content(extraction_prompt)
        cleaned_json = result.text.replace("```json", "").replace("```", "").strip()
        tools_list = json.loads(cleaned_json)
        if isinstance(tools_list, dict):
            tools_list = [tools_list]
        return tools_list
    except:
        return []

def update_csv_single_tool(action_type, tool_data):
    """
    개별 도구(tool_data) 하나를 CSV에 업데이트
    """
    try:
        if os.path.exists(CSV_FILE_PATH):
            df = pd.read_csv(CSV_FILE_PATH, encoding='utf-8-sig', on_bad_lines='skip')
        else:
            return False, "CSV 파일이 없습니다."

        if '비추천수' not in df.columns:
            df['비추천수'] = 0

        target_tool = tool_data.get('추천도구')
        if not target_tool: return False, "도구명이 없습니다."

        # CASE 1: 👍 좋아요
        if action_type == 'like':
            if target_tool in df['추천도구'].values:
                return False, f"⚠️ '{target_tool}'은(는) 이미 있습니다."
            else:
                tool_data['비추천수'] = 0
                new_row = pd.DataFrame([tool_data])
                df = pd.concat([df, new_row], ignore_index=True)
                df.to_csv(CSV_FILE_PATH, index=False, encoding='utf-8-sig')
                return True, f"✅ '{target_tool}' 저장 완료!"

        # CASE 2: 👎 싫어요
        elif action_type == 'dislike':
            if target_tool not in df['추천도구'].values:
                return False, f"❓ '{target_tool}'(DB에 없음)"
            else:
                idx = df[df['추천도구'] == target_tool].index
                df.loc[idx, '비추천수'] += 1
                current = df.loc[idx, '비추천수'].values[0]
                
                msg = ""
                if current >= 3:
                    df = df.drop(idx)
                    msg = f"🗑️ '{target_tool}' 삭제됨 (3회 누적)"
                else:
                    msg = f"📉 '{target_tool}' 비추천 ({current}/3)"
                
                df.to_csv(CSV_FILE_PATH, index=False, encoding='utf-8-sig')
                return True, msg
                
    except Exception as e:
        return False, f"오류: {str(e)}"

# ==========================================
# 3. 사이드바 (UI)
# ==========================================
with st.sidebar:
    st.title("🎛️ 추천 옵션")
    
    if "sb_job" not in st.session_state:
        st.session_state.sb_job = "직접 입력"
    if "sb_situation" not in st.session_state:
        st.session_state.sb_situation = "직접 입력"

    selected_job = "직접 입력"
    selected_situation = "직접 입력"
    
    if df_tools is not None:
        st.success(f"✅ DB 연동됨 ({len(df_tools)}개 도구)")
        
        job_list = sorted(df_tools['직무'].unique().tolist())
        selected_job = st.selectbox("직무를 선택하세요", ["직접 입력"] + job_list, key="sb_job")
        
        if selected_job != "직접 입력":
            situation_list = sorted(df_tools[df_tools['직무'] == selected_job]['상황'].unique().tolist())
            selected_situation = st.selectbox("어떤 상황인가요?", ["직접 입력"] + situation_list, key="sb_situation")
    else:
        st.error("CSV 파일을 찾지 못했습니다.")
    
    st.divider()
    
    output_format = st.multiselect(
        "필요한 결과물 양식",
        ["보고서(텍스트)", "PPT(발표자료)", "이미지", "영상", "표(Excel)", "요약본"],
        default=[]
    )
    
    st.caption("ⓒ 2024 Job-Fit AI Navigator")

# ==========================================
# 4. AI 모델 설정 (하이브리드 추천)
# ==========================================
csv_context = ""
if df_tools is not None:
    display_cols = [col for col in df_tools.columns if col != '비추천수']
    csv_context = f"""
    [우리가 보유한 검증된 도구 목록 (DB)]
    {df_tools[display_cols].to_string(index=False)}
    """

sys_instruction = f"""
너는 트렌디하고 스마트한 'AI 도구 큐레이터'야.
사용자의 직무와 상황을 듣고 가장 '적합한' 도구를 추천해줘.

### 🎯 핵심 추천 전략:
1. **하이브리드 추천:** [검증된 도구 목록]을 참고하되, 목록에 없더라도 네가 알고 있는 최신/고성능 도구가 있다면 적극적으로 추천해줘.
2. **비율:** 가능하면 **(DB에 있는 도구) + (새로운 도구)**를 섞어서 제안해줘.
3. **판단 기준:** 무조건 **'사용자 상황 해결'**이 1순위야.

### 📝 답변 작성 포맷:
1. **공감 및 분석:** 상황에 대한 짧은 공감
2. **추천 도구 (1~3개):**
   - 🔧 **도구명:** (정확한 명칭)
   - 💡 **추천 이유:** (이 상황에 왜 강점인지)
   - 💰 **가격:** (무료 / 유료 / 부분유료)
   - 🔗 **링크:** (URL)
   - ✨ **꿀팁:** (실무 활용 팁)

3. **마무리:** "이 도구가 마음에 드시면 👍를 눌러주세요! 다음에 기억해 둘게요."

{csv_context}
"""

# 무료 사용량이 넉넉한 Flash 모델 사용 (Pro는 50회 제한으로 에러 가능성 높음)
model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=sys_instruction)

# ==========================================
# 5. 메인 채팅 인터페이스
# ==========================================
st.title("🚀 Job-Fit AI 네비게이터")

welcome_msg = """
👋 **반가워요! 당신의 스마트한 업무 파트너, Job-Fit AI입니다.**

"이럴 땐 어떤 AI를 써야 하지?" 더 이상 혼자 고민하지 마세요.
상황을 말씀해 주시면 제가 딱 맞는 도구를 찾아드릴게요. 

💁‍♀️ **사용 꿀팁!**
1. **👈 왼쪽 사이드바**에서 직무를 선택하면 버튼 하나로 편하게 질문할 수 있어요.
2. 혹은 아래 채팅창에 **친구에게 묻듯 구체적으로** 물어보세요.
   * "마케터인데 무료로 쓸 수 있는 이미지 생성 툴 있어?"
   * "회의록 정리가 너무 귀찮은데 도와줄 AI 추천해 줘!"

마음에 드는 추천에는 **따봉(👍)**을 눌러주시면 제가 꼭 기억해 둘게요!
(도움이 되셨다면 [GitHub](https://github.com/Timber-Fit/Job-Fit-AI-Navigator)에서 **Star(⭐)**도 부탁드려요!)
"""
st.markdown(welcome_msg)

if "messages" not in st.session_state:
    st.session_state.messages = []

# 대화 내용 표시
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # AI 답변 아래에만 '도구 관리' 버튼 표시
        if message["role"] == "assistant":
            # 이 메시지에 'extracted_tools'가 저장되어 있는지 확인
            tools_key = f"tools_{i}"
            
            # [Step 1] 아직 분석 안 된 상태면 '분석 버튼' 보여주기
            if tools_key not in st.session_state:
                if st.button("🛠️ 이 답변의 도구 저장/비추천 관리하기", key=f"analyze_{i}"):
                    with st.spinner("답변에서 도구 정보를 추출하는 중..."):
                        # 이전 사용자 질문 가져오기
                        user_query = st.session_state.messages[i-1]["content"] if i > 0 else ""
                        ai_text = message["content"]
                        
                        # API 호출해서 도구 리스트 뽑기
                        tools_found = parse_tools_from_text(user_query, ai_text)
                        
                        if tools_found:
                            st.session_state[tools_key] = tools_found
                            st.rerun() # 화면 갱신해서 목록 보여주기
                        else:
                            st.error("추출된 도구가 없습니다.")
            
            # [Step 2] 분석된 도구가 있으면 -> 개별 버튼 뿌리기
            else:
                tools_list = st.session_state[tools_key]
                st.caption(f"💡 {len(tools_list)}개의 도구를 찾았습니다. 개별적으로 저장하거나 비추천할 수 있습니다.")
                
                for tool in tools_list:
                    t_name = tool['추천도구']
                    
                    # 카드 형태로 보여주기 (컬럼 사용)
                    c1, c2, c3 = st.columns([3, 1, 1])
                    with c1:
                        st.markdown(f"**🔧 {t_name}**")
                    with c2:
                        if st.button("👍저장", key=f"save_{i}_{t_name}"):
                            success, msg = update_csv_single_tool('like', tool)
                            if success: 
                                st.toast(msg, icon="✅")
                                st.cache_data.clear()
                                st.rerun()
                            else: st.toast(msg, icon="⚠️")
                    with c3:
                        if st.button("👎비추", key=f"del_{i}_{t_name}"):
                            success, msg = update_csv_single_tool('dislike', tool)
                            if success: 
                                st.toast(msg, icon="📉")
                                st.cache_data.clear()
                                st.rerun()
                            else: st.toast(msg, icon="⚠️")

# [콜백 함수] 사이드바 초기화
def handle_quick_recommendation(job, situation):
    auto_prompt = f"나는 '{job}' 직무를 맡고 있어. 현재 '{situation}' 업무를 해야 하는데 적합한 AI 도구를 추천해줘."
    st.session_state.messages.append({"role": "user", "content": auto_prompt})
    st.session_state["sb_job"] = "직접 입력"
    st.session_state["sb_situation"] = "직접 입력"

def reset_conversation():
    st.session_state.messages = []
    st.session_state["sb_job"] = "직접 입력"
    st.session_state["sb_situation"] = "직접 입력"
    # 도구 분석 캐시도 날리기 위해 keys 확인
    keys_to_del = [k for k in st.session_state.keys() if k.startswith("tools_")]
    for k in keys_to_del:
        del st.session_state[k]

# 버튼 영역
col1, col2 = st.columns([8, 2])
with col2:
    st.button("🔄 새로운 대화 시작", on_click=reset_conversation, use_container_width=True)
with col1:
    if selected_job != "직접 입력" and selected_situation != "직접 입력":
        btn_label = f"🔍 '{selected_job}' - '{selected_situation}' 추천받기"
        st.button(btn_label, type="primary", on_click=handle_quick_recommendation, args=(selected_job, selected_situation), use_container_width=True)

# 직접 질문
if prompt := st.chat_input("질문하기..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

# AI 답변 생성
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        msg_placeholder = st.empty()
        with st.spinner("생각 중..."):
            try:
                # [핵심 수정] Gemini History 형식에 맞게 변환 (user/model)
                gemini_history = []
                for m in st.session_state.messages[:-1]: # 마지막 질문 제외
                    role = "user" if m["role"] == "user" else "model"
                    gemini_history.append({"role": role, "parts": [m["content"]]})
                
                chat = model.start_chat(history=gemini_history)
                response = chat.send_message(st.session_state.messages[-1]["content"])
                
                msg_placeholder.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun()
            except Exception as e:
                msg_placeholder.error(f"오류: {e}")
                st.session_state.messages.pop() 