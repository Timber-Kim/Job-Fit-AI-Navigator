import streamlit as st

# -----------------------------------------------------------
# 0. Session State 초기값 설정
# -----------------------------------------------------------
if "selected_role" not in st.session_state:
    st.session_state.selected_role = "전체"

if "selected_output" not in st.session_state:
    st.session_state.selected_output = "전체"

if "search_keyword" not in st.session_state:
    st.session_state.search_keyword = ""


# -----------------------------------------------------------
# 1. 추천 데이터 (네가 준 데이터셋을 Python 리스트로 변환)
#    직무, 상황, 결과물, 추천도구, 특징_및_팁, 유료여부, 링크
# -----------------------------------------------------------
tools_data = [
    {
        "role": "공통",
        "situation": "자료 조사 및 검색",
        "output": "요약 텍스트",
        "name": "Perplexity",
        "desc": "출처가 명시되어 팩트 체크 필수인 업무에 최적화 (할루시네이션 적음)",
        "paid": "부분유료",
        "link": "https://www.perplexity.ai/"
    },
    {
        "role": "공통",
        "situation": "긴 글 작성 및 초안",
        "output": "보고서/메일",
        "name": "Claude 3.5 Sonnet",
        "desc": "사람처럼 자연스러운 문체와 긴 문맥 이해력 (보고서 초안용)",
        "paid": "부분유료",
        "link": "https://claude.ai/"
    },
    {
        "role": "공통",
        "situation": "외국어 번역",
        "output": "번역 텍스트",
        "name": "DeepL",
        "desc": "전문 용어와 뉘앙스를 살린 고품질 번역 (파일 통번역 가능)",
        "paid": "부분유료",
        "link": "https://www.deepl.com/"
    },
    {
        "role": "공통",
        "situation": "회의 녹음 및 속기",
        "output": "회의록",
        "name": "Clova Note",
        "desc": "한국어 인식률 최상, 화자 분리 및 핵심 요약 기능 탁월",
        "paid": "무료/부분유료",
        "link": "https://clovanote.naver.com/"
    },
    {
        "role": "공통",
        "situation": "유튜브 영상 요약",
        "output": "요약 노트",
        "name": "Lilys",
        "desc": "긴 영상의 핵심 내용을 타임라인별로 요약하여 블로그/문서로 변환",
        "paid": "부분유료",
        "link": "https://lilys.ai/"
    },
    {
        "role": "공무원/공공",
        "situation": "보도자료 및 공문서 초안",
        "output": "초안 텍스트",
        "name": "Wrtn (뤼튼)",
        "desc": "GPT-4 기반 무료 사용 가능, 한국어 공문서 말투 생성에 강점",
        "paid": "무료/부분유료",
        "link": "https://wrtn.ai/"
    },
    {
        "role": "공무원/공공",
        "situation": "문서 편집 및 변환",
        "output": "HWP/문서",
        "name": "Polaris Office AI",
        "desc": "HWP 파일 열람 및 AI를 통한 문장 다듬기/요약 기능 지원",
        "paid": "부분유료",
        "link": "https://www.polarisoffice.com/"
    },
    {
        "role": "공무원/공공",
        "situation": "국내 정책 및 정보 검색",
        "output": "검색 결과",
        "name": "Naver Cue:",
        "desc": "네이버 데이터 기반으로 국내 정보/정책 검색에 특화됨",
        "paid": "무료",
        "link": "https://cue.naver.com/"
    },
    {
        "role": "금융/재무",
        "situation": "복잡한 데이터 분석",
        "output": "시각화 차트",
        "name": "Julius AI",
        "desc": "엑셀/CSV 파일을 올리면 대화형으로 분석하고 차트 생성 (파이썬 기반)",
        "paid": "유료",
        "link": "https://julius.ai/"
    },
    {
        "role": "금융/재무",
        "situation": "금융 보고서/PDF 분석",
        "output": "요약 및 답변",
        "name": "ChatDOC",
        "desc": "수백 장의 금융 보고서를 읽고 정확한 수치 기반 답변 제공 (출처 표시)",
        "paid": "부분유료",
        "link": "https://chatdoc.com/"
    },
    {
        "role": "금융/재무",
        "situation": "시장 리서치 및 전망",
        "output": "리서치 리포트",
        "name": "ChatGPT (Data Analyst)",
        "desc": "웹 검색과 데이터 분석 기능을 결합해 시장 동향 파악에 용이",
        "paid": "부분유료",
        "link": "https://chat.openai.com/"
    },
    {
        "role": "기획자(PM)",
        "situation": "기획안 시각화/마인드맵",
        "output": "다이어그램",
        "name": "Whimsical AI",
        "desc": "텍스트로 아이디어를 입력하면 마인드맵과 플로우차트 자동 생성",
        "paid": "부분유료",
        "link": "https://whimsical.com/ai"
    },
    {
        "role": "기획자(PM)",
        "situation": "문서 정리 및 프로젝트 관리",
        "output": "노션 페이지",
        "name": "Notion AI",
        "desc": "지저분한 메모를 깔끔한 기획서로 정리 및 투두 리스트 추출",
        "paid": "유료",
        "link": "https://www.notion.so/product/ai"
    },
    {
        "role": "기획자(PM)",
        "situation": "설문조사 결과 분석",
        "output": "인사이트 리포트",
        "name": "ChatGPT (Canvas)",
        "desc": "설문 응답 데이터를 업로드하면 주요 패턴과 인사이트 도출",
        "paid": "부분유료",
        "link": "https://chat.openai.com/"
    },
    {
        "role": "마케터",
        "situation": "PPT 기획 및 디자인",
        "output": "PPT 슬라이드",
        "name": "Gamma",
        "desc": "주제만 입력하면 목차부터 고품질 디자인 슬라이드 자동 생성",
        "paid": "부분유료",
        "link": "https://gamma.app/"
    },
    {
        "role": "마케터",
        "situation": "블로그/SNS 마케팅 문구",
        "output": "광고 카피",
        "name": "Copy.ai",
        "desc": "다양한 마케팅 프레임워크(AIDA 등)에 맞춘 카피라이팅 특화",
        "paid": "유료",
        "link": "https://www.copy.ai/"
    },
    {
        "role": "마케터",
        "situation": "광고용 이미지 생성",
        "output": "이미지",
        "name": "Midjourney",
        "desc": "예술적이고 창의적인 고퀄리티 이미지 생성 (디스코드 사용)",
        "paid": "유료",
        "link": "https://www.midjourney.com/"
    },
    {
        "role": "마케터",
        "situation": "영상 숏폼 제작",
        "output": "숏폼 영상",
        "name": "Vrew",
        "desc": "대본만 넣으면 AI 목소리와 무료 이미지를 매칭해 영상 자동 생성",
        "paid": "부분유료",
        "link": "https://vrew.voyagerx.com/"
    },
    {
        "role": "인사(HR)",
        "situation": "채용 공고 및 JD 작성",
        "output": "채용 공고문",
        "name": "Jasper",
        "desc": "기업 톤앤매너에 맞춘 전문적인 비즈니스 글쓰기 지원",
        "paid": "유료",
        "link": "https://www.jasper.ai/"
    },
    {
        "role": "인사(HR)",
        "situation": "온보딩 자료 제작",
        "output": "교육 자료",
        "name": "Synthesia",
        "desc": "텍스트를 입력하면 AI 아바타가 설명하는 교육 영상 생성",
        "paid": "유료",
        "link": "https://www.synthesia.io/"
    },
    {
        "role": "영업(Sales)",
        "situation": "콜드 메일 작성",
        "output": "이메일 초안",
        "name": "ChatGPT (GPT-4)",
        "desc": "고객 페르소나를 설정하여 거부감 없는 제안 메일 작성 가능",
        "paid": "부분유료",
        "link": "https://chat.openai.com/"
    },
    {
        "role": "디자이너",
        "situation": "이미지 편집 및 확장",
        "output": "이미지",
        "name": "Adobe Firefly",
        "desc": "포토샵 생성형 채우기 기능, 저작권 문제 없이 상업적 이용 가능",
        "paid": "유료",
        "link": "https://firefly.adobe.com/"
    },
    {
        "role": "디자이너",
        "situation": "상세페이지/배너",
        "output": "디자인 시안",
        "name": "Canva Magic Studio",
        "desc": "명령어로 SNS 게시물, 배너 등 디자인 템플릿 즉시 생성",
        "paid": "부분유료",
        "link": "https://www.canva.com/"
    },
    {
        "role": "개발자",
        "situation": "코드 작성 및 디버깅",
        "output": "소스 코드",
        "name": "Cursor",
        "desc": "VS Code 기반 AI 에디터, 프로젝트 전체 구조를 이해하고 코딩 지원",
        "paid": "부분유료",
        "link": "https://www.cursor.com/"
    },
    {
        "role": "개발자",
        "situation": "코드 자동 완성",
        "output": "코드 조각",
        "name": "GitHub Copilot",
        "desc": "주석이나 함수명만 쓰면 코드를 자동 완성 (생산성 표준 도구)",
        "paid": "유료",
        "link": "https://github.com/features/copilot"
    },
    {
        "role": "대학생/연구원",
        "situation": "논문 분석 및 요약",
        "output": "PDF 요약",
        "name": "ChatPDF",
        "desc": "논문 PDF를 업로드하면 내용을 파악하고 질문에 답변",
        "paid": "부분유료",
        "link": "https://www.chatpdf.com/"
    },
    {
        "role": "대학생/연구원",
        "situation": "학술 검색 및 리서치",
        "output": "논문 리스트",
        "name": "Consensus",
        "desc": "질문을 던지면 관련 논문을 근거로 과학적 답변 생성",
        "paid": "부분유료",
        "link": "https://consensus.app/"
    },
    {
        "role": "크리에이터",
        "situation": "텍스트 음성 변환(TTS)",
        "output": "음성 파일",
        "name": "ElevenLabs",
        "desc": "가장 자연스럽고 감정 표현이 가능한 AI 목소리 생성",
        "paid": "유료",
        "link": "https://elevenlabs.io/"
    },
    {
        "role": "크리에이터",
        "situation": "배경 음악 생성",
        "output": "음악(BGM)",
        "name": "Suno AI",
        "desc": "원하는 장르와 분위기를 입력하면 보컬 곡/연주 곡 생성",
        "paid": "부분유료",
        "link": "https://suno.com/"
    },
    {
        "role": "직장인(총무)",
        "situation": "업무 자동화",
        "output": "워크플로우",
        "name": "Zapier",
        "desc": "코딩 없이 지메일, 슬랙, 노션 등을 연결해 반복 업무 자동화",
        "paid": "부분유료",
        "link": "https://zapier.com/"
    }
]


# -----------------------------------------------------------
# 2. UI 구성
# -----------------------------------------------------------
st.title("🤖 직무·상황별 AI 툴 추천기")
st.subheader("직무, 상황, 결과물 기준으로 최적의 AI 도구를 찾아줍니다.")

st.sidebar.header("필터")

roles = sorted({item["role"] for item in tools_data})
outputs = sorted({item["output"] for item in tools_data})

st.session_state.selected_role = st.sidebar.selectbox(
    "직무",
    ["전체"] + roles,
    index=(["전체"] + roles).index(st.session_state.selected_role)
)

st.session_state.selected_output = st.sidebar.selectbox(
    "결과물 종류",
    ["전체"] + outputs,
    index=(["전체"] + outputs).index(st.session_state.selected_output)
)

st.session_state.search_keyword = st.sidebar.text_input(
    "상황 키워드 (예: 보고서, 숏폼, 번역)",
    st.session_state.search_keyword
)

# 필터 초기화
if st.sidebar.button("필터 초기화"):
    st.session_state.selected_role = "전체"
    st.session_state.selected_output = "전체"
    st.session_state.search_keyword = ""
    st.experimental_rerun()


# -----------------------------------------------------------
# 3. 추천 로직
# -----------------------------------------------------------
recommendations = []
for tool in tools_data:
    if st.session_state.selected_role != "전체" and tool["role"] != st.session_state.selected_role:
        continue
    if st.session_state.selected_output != "전체" and tool["output"] != st.session_state.selected_output:
        continue
    if st.session_state.search_keyword and st.session_state.search_keyword not in tool["situation"]:
        continue
    recommendations.append(tool)


# -----------------------------------------------------------
# 4. 결과 출력
# -----------------------------------------------------------
st.divider()

if recommendations:
    st.success(f"총 {len(recommendations)}개의 도구를 찾았습니다.")
    for tool in recommendations:
        with st.expander(f"🛠️ {tool['name']} | {tool['role']} | {tool['output']}"):
            st.markdown(f"**상황**  : {tool['situation']}")
            st.markdown(f"**특징/팁** : {tool['desc']}")
            st.markdown(f"**유료 여부** : {tool['paid']}")
            if tool["link"]:
                st.markdown(f"[🔗 도구 바로가기]({tool['link']})")
else:
    st.warning("조건에 맞는 도구를 찾지 못했습니다. 필터를 조금 넓혀보세요.")
