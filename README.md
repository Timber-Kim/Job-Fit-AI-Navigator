# Job-Fit-AI-Navigator

> **어떤 AI를 써야 할지 모르겠다면?
직무와 상황만 알려주세요. 최적의 AI를 바로 찾아드립니다.**
> If you're not sure which AI tool to use, just tell us your job and situation — we'll recommend the perfect one instantly.

## 📖 프로젝트 소개 (About)
**Job-Fit AI Navigator**는 수많은 AI 서비스 속에서
사용자에게 가장 잘 맞는 최적의 AI 도구를 자동으로 추천하는 메타 AI 서비스입니다.

쏟아지는 AI 서비스 홍수 속에서,
이미 존재하는 다양한 AI 도구들을 직무(Job) × 상황(Situation) × 결과물(Output) 기준으로 연결해 주는
AI 메타 라우터(Meta AI) 를 목표로 합니다.

이 프로젝트는 단순한 “인기있는 AI 리스트”가 아니라,
실무자가 실제로 맞닥뜨리는 구체적인 페인 포인트를 해결하는 솔루션입니다.

## 🌊 Why We Started

요즘은 정말로 매일 새로운 AI 툴이 쏟아지는 시대입니다.
하지만 실무자들은 오히려 이렇게 말합니다.

“AI 너무 많은데, 어떤 걸 써야 해?”

“내 일이랑 맞는 AI가 뭔지 모름…”

“툴 비교하다가 시간만 더 씀…”

문제는 ‘좋은 AI가 없는 게 아니라, 너무 많다는 것’.
이 선택의 과부하를 해결하기 위해 프로젝트가 시작되었습니다.

“최신이면서, 지금 내 상황에 최적화된 AI를
검색 없이 바로 추천받을 수 없을까?”

이 고민에서 출발해,
우리는 AI를 분류·큐레이션·필터링해주는 AI 메타 추천 플랫폼을 설계했고,
그 결과가 바로 **Job-Fit AI Navigator**입니다.


## 🚀 주요 기능 (Features)
- **직무별 큐레이션**: 마케터, 개발자, 기획자, 디자이너 등 직군별 최적화된 AI를 분류합니다.
  
- **상황별 매칭**: 리서치, 브레인스토밍, 보고서 작성, 디자인 생성, PPT 제작 등 “지금 이 상황”에 최적화된 AI를 자동 추천합니다.
  
- **워크플로우 레시피 제공**: 단일 AI 추천을 넘어, 여러 AI를 조합해 “최적의 AI 조합(Recipe)”을 제시합니다.
  ex) Perplexity → 해외 리서치, Claude → 보고서 초안, Gamma → PPT 자동 생성
  
- **CSV 기반 추천 엔진 고도화** : 내부 DB를 기반으로 AI 정보를 관리합니다.
  새로운 AI 도구는 DB에 자동 추가되며, 적합하지 않은 도구는 비추천 기능을 통해 자동으로 제외됩니다.
  
- **사용자 피드백 기반 자동 학습** : 👎 비추천 3회 → CSV DB에서 해당 AI 자동 삭제, 👍 새로운 AI 도구 입력 후 추천 → CSV DB에 자동 추가
  사용할수록 추천 품질이 좋아지는 구조입니다.

## ⚙️ How It Works
<img width="1902" height="837" alt="image" src="https://github.com/user-attachments/assets/e6ec31b0-8aa8-4c27-8799-e1c49bfb2e32" />

🔍 1. 사용자 입력

자유롭게 텍스트로 입력하면 됩니다.

예: “나는 마케팅팀인데 이번 주 안에 광고 이미지랑 카피를 만들어야 해.”

🧠 2. LLM이 입력을 구조화

Job: 마케터

Situation: 콘텐츠 제작

Output: 이미지 + 카피

🔎 3. CSV DB에서 필터링

직무 + 상황 + 결과물 기준으로
해당 상황에 맞는 AI 도구만 추출.

🧩 4. 우선순위 스코어링

신뢰성

난이도

가격(무료/유료)

속도
이 요소를 기준으로 적합도 점수를 계산.

🔁 5. 사용자 피드백 반영

비추천 3회 → 자동 제거

추천된 새 도구 → 자동 추가
→ 시간이 지날수록 더 똑똑해지는 추천 엔진 완성.

## 📂 추천 목록 예시 (Preview)

| 상황 (Situation) | 추천 도구 (Tool) | 활용 팁 (Tip) |
| :--- | :--- | :--- |
| **해외 시장 리서치** | **Perplexity** | 출처가 명시된 답변을 제공하므로 팩트 체크에 유리합니다. |
| **사업 제안서 초안** | **Claude 3.5 Sonnet** | 논리적인 글쓰기와 문맥 파악 능력이 뛰어나 초안 작성에 탁월합니다. |
| **발표용 PPT 생성** | **Gamma** | 텍스트 개요만 넣으면 디자인된 슬라이드를 자동 생성합니다. |

*실제 추천 결과는 사용자 입력과 DB, 그리고 누적된 피드백에 따라 달라집니다.*

## 🗂️ Database & Web Demo

CSV Database (Google Spreadsheet)
👉 https://docs.google.com/spreadsheets/d/176EoAIiDYnDiD9hORKABr_juIgRZZss5ApTqdaRCx5E/edit?gid=0#gid=0

웹 데모 (Streamlit)
👉 https://job-fit-ai-navigator-dfpc8ttxmdtugtappucmjyb.streamlit.app/#job-fit-ai

## 🛠️ 향후 로드맵 (Roadmap)
이 프로젝트는 단순 리스트업을 넘어, Python 기반의 추천 알고리즘을 도입할 예정입니다.
- [x] 초기 데이터셋 구축 (엑셀/CSV)
- [ ] 사용자 입력 기반 추천 알고리즘 (Rule-based) 구현
- [ ] LLM 기반 자연어 의도 파악 및 툴 추천 챗봇 개발
- [ ] 웹 데모 페이지 (Streamlit) 배포

## 🤝 기여하기 (Contribution)
여러분이 알고 있는 '꿀팁' AI 도구가 있다면 제보해 주세요!
1. 이 저장소를 **Star(⭐️)** 눌러주세요.
2. `Issues` 탭에 새로운 AI 도구 제안하거나, `Pull Request`를 보내주세요.



“AI를 잘 쓰는 사람”보다,
“AI를 잘 골라 쓰는 사람”이 경쟁력이 되는 시대.
**Job-Fit AI Navigator**가 그 사이를 이어주는 브릿지가 되겠습니다.

---
Created by [2025-2 인간-인공지능협업제품서비스설계 / 3팀]
