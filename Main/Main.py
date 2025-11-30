import streamlit as st
import google.generativeai as genai
import pandas as pd
import os
import json
import time  # [추가] 시간을 지연시키기 위해 필요합니다!

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

# 데이터 초기화 함수 (메모리 우선)
def init_data():
    if "master_df" not in st.session_state:
        if os.path.exists(CSV_FILE_PATH):
            try:
                df = pd.read_csv(CSV_FILE_PATH, encoding='utf-8-sig', on_bad_lines='skip')
            except:
                try:
                    df = pd.read_csv(CSV_FILE_PATH, encoding='cp949', on_bad_lines='skip')
                except:
                    df = pd.DataFrame(columns=['직무','상황','결과물','추천도구','특징_및_팁','유료여부','링크','비추천수'])
        else:
            df = pd.DataFrame(columns=['직무','상황','결과물','추천도구','특징_및_팁','유료여부','링크','비추천수'])
        
        if '비추천수' not in df.columns:
            df['비추천수'] = 0
            
        st.session_state.master_df = df

init_data()
df_tools = st.session_state.master_df

# ==========================================
# 2. 도구 정보 추출 및 데이터 업데이트 로직
# ==========================================
def parse_tools_from_text(user_text, ai_text):
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

def update_data_single_tool(action_type, tool_data):
    df = st.session_state.master_df
    target_tool = tool_data.get('추천도구')
    
    if not target_tool: return False, "도구명이 없습니다."

    try:
        msg = ""
        success = True

        # CASE 1: 👍 좋아요
        if action_type == 'like':
            if target_tool in df['추천도구'].values:
                idx = df[df['추천도구'] == target_tool].index
                current_dislike = st.session_state.master_df.loc[idx, '비추천수'].values[0]
                
                if current_dislike > 0:
                    st.session_state.master_df.loc[idx, '비추천수'] -= 1
                    msg = f"✅ '{target_tool}' 비추천 1회 차감! (현재 {st.session_state.master_df.loc[idx, '비추천수'].values[0]})"
                else:
                    msg = f"✨ '{target_tool}'은(는) 이미 안전하게 저장되어 있습니다."
            else:
                tool_data['비추천수'] = 0
                new_row = pd.DataFrame([tool_data])
                st.session_state.master_df = pd.concat([df, new_row], ignore_index=True)
                msg = f"🎉 '{target_tool}' 데이터베이스에 새로 저장 완료!"

        # CASE 2: 👎 싫어요
        elif action_type == 'dislike':
            if target_tool not in df['추천도구'].values:
                return False, f"❓ '{target_tool}'은(는) 아직 저장되지 않은 도구입니다."
            else:
                idx = df[df['추천도구'] == target_tool].index
                st.session_state.master_df.loc[idx, '비추천수'] += 1
                current = st.session_state.master_df.loc[idx, '비추천수'].values[0]
                
                if current >= 3:
                    st.session_state.master_df = st.session_state.master_df.drop(idx).reset_index(drop=True)
                    msg = f"🗑️ '{target_tool}' 삭제됨 (비추천 3회 누적)"
                else:
                    msg = f"📉 '{target_tool}' 비추천 ({current}/3회)"

        # 파일 저장 시도
        try:
            st.session_state.master_df.to_csv(CSV_FILE_PATH, index=False, encoding='utf-8-sig')
        except:
            pass 

        return success, msg
                
    except Exception as e:
        return False, f"오류: {str(e)}"

# [콜백 함수] 대화 및 상태 초기화
def reset_conversation():
    st.session_state.messages = []
    st.session_state["sb_job"] = "직접 입력"
    st.session_state["sb_situation"] = "직접 입력"
    st.session_state["sb_output_format"] = []
    
    keys_to_del = [k for k in st.session_state.keys() if k.startswith("tools_")]
    for k in keys_to_del:
        del st.session_state[k]

# ==========================================
# 3. 사이드바 (UI)
# ==========================================
with st.sidebar:

    st.title("🎛️ 메뉴")

    st.divider()

    if "sb_job" not in st.session_state: st.session_state.sb_job = "직접 입력"
    if "sb_situation" not in st.session_state: st.session_state.sb_situation = "직접 입력"
    if "sb_output_format" not in st.session_state: st.session_state.sb_output_format = []

    selected_job = "직접 입력"
    selected_situation = "직접 입력"
    
    if not df_tools.empty:
        st.success(f"✅ DB 연동됨 ({len(df_tools)}개 도구)")
        
        job_list = sorted(df_tools['직무'].astype(str).unique().tolist())
        selected_job = st.selectbox("직무를 선택하세요", ["직접 입력"] + job_list, key="sb_job")
        
        if selected_job != "직접 입력":
            situation_list = sorted(df_tools[df_tools['직무'] == selected_job]['상황'].astype(str).unique().tolist())
            selected_situation = st.selectbox("어떤 상황인가요?", ["직접 입력"] + situation_list, key="sb_situation")
    else:
        st.warning("데이터가 비어있습니다.")
    
    st.divider()
    
    output_format = st.multiselect(
        "필요한 결과물 양식 (다중 선택 가능)",
        ["보고서(텍스트)", "PPT(발표자료)", "이미지", "영상", "표(Excel)", "요약본", "코드"],
        default=[],
        key="sb_output_format"
    )
    st.divider()

    st.button("🔄 새로운 대화 시작", on_click=reset_conversation, use_container_width=True)

    st.divider()

    st.caption("ⓒ 2025 Job-Fit AI Navigator")

# ==========================================
# 4. AI 모델 설정
# ==========================================
csv_context = ""
if not df_tools.empty:
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
(도움이 되셨다면 [GitHub](https://github.com/Timber-Kim/Job-Fit-AI-Navigator)에서 **Star(⭐)**도 부탁드려요!)
"""
st.markdown(welcome_msg)

if "messages" not in st.session_state:
    st.session_state.messages = []

# 대화 내용 표시
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        if message["role"] == "assistant":
            tools_key = f"tools_{i}"
            
            if tools_key not in st.session_state:
                if st.button("🛠️ 이 답변의 도구 추천/비추천 관리하기", key=f"analyze_{i}"):
                    with st.spinner("답변에서 도구 정보를 추출하는 중..."):
                        user_query = st.session_state.messages[i-1]["content"] if i > 0 else ""
                        ai_text = message["content"]
                        tools_found = parse_tools_from_text(user_query, ai_text)
                        
                        if tools_found:
                            st.session_state[tools_key] = tools_found
                            st.rerun()
                        else:
                            st.error("추출된 도구가 없습니다.")
            else:
                tools_list = st.session_state[tools_key]
                st.caption(f"💡 {len(tools_list)}개의 도구를 찾았습니다.")
                
                for tool in tools_list:
                    t_name = tool['추천도구']
                    c1, c2, c3 = st.columns([3, 1, 1])
                    with c1: st.markdown(f"**🔧 {t_name}**")
                    with c2:
                        if st.button("👍추천", key=f"save_{i}_{t_name}"):
                            success, msg = update_data_single_tool('like', tool)
                            if success: 
                                st.toast(msg, icon="✅")
                                time.sleep(2) # [추가] 2초 대기하여 메시지를 읽을 시간을 줌
                                st.rerun()
                            else: 
                                st.toast(msg, icon="⚠️")
                                time.sleep(2) # [추가] 
                                st.rerun() # 실패 메시지도 보고 넘어가도록
                    with c3:
                        if st.button("👎비추", key=f"del_{i}_{t_name}"):
                            success, msg = update_data_single_tool('dislike', tool)
                            if success: 
                                st.toast(msg, icon="📉")
                                time.sleep(2) # [추가]
                                st.rerun()
                            else: 
                                if msg != "SILENT":
                                    st.toast(msg, icon="⚠️")
                                    time.sleep(2) # [추가]
                                    st.rerun()

# [콜백 함수]
def handle_quick_recommendation(job, situation, outputs):
    tools_str = ", ".join(outputs) if outputs else "특별히 지정하지 않음"
    auto_prompt = f"나는 '{job}' 직무를 맡고 있어. 현재 '{situation}' 업무를 해야 하고, 필요한 결과물은 '{tools_str}' 야. 적합한 AI 도구를 추천해줘."
    
    st.session_state.messages.append({"role": "user", "content": auto_prompt})
    st.session_state["sb_job"] = "직접 입력"
    st.session_state["sb_situation"] = "직접 입력"
    st.session_state["sb_output_format"] = []

if selected_job != "직접 입력" and selected_situation != "직접 입력":
    btn_label = f"🔍 '{selected_job}' - '{selected_situation}' 추천받기"
    st.button(btn_label, type="primary", on_click=handle_quick_recommendation, args=(selected_job, selected_situation, output_format), use_container_width=True)

if prompt := st.chat_input("직접 질문하기 (예: 무료로 쓸 수 있는 PPT 도구 있어?)"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        msg_placeholder = st.empty()
        with st.spinner("생각 중..."):
            try:
                gemini_history = []
                for m in st.session_state.messages[:-1]: 
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
                st.rerun()