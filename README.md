# Job-Fit-AI-Navigator

**어떤 AI를 써야 할지 모르겠다면?
직무와 상황만 알려주세요. 최적의 AI를 바로 찾아드립니다.**

>If you're not sure which AI tool to use, just tell us your job and situation — we'll recommend the perfect one instantly.


<br>
<br>

## 📖 프로젝트 소개 (About)
**Job-Fit AI Navigator**는 수많은 AI 서비스 속에서
사용자에게 가장 잘 맞는 최적의 AI 도구를 자동으로 추천하는 메타 AI 서비스입니다.

>Job-Fit AI Navigator is a meta AI service that automatically recommends the most suitable AI tools for each user from the overwhelming number of AI services.


쏟아지는 AI 서비스 홍수 속에서,
이미 존재하는 다양한 AI 도구들을 직무(Job) × 상황(Situation) × 결과물(Output) 기준으로 연결해 주는
AI 메타 라우터(Meta AI) 를 목표로 합니다.

>Our goal is to act as a Meta AI Router, intelligently matching users to the best tool based on Job × Situation × Output.


이 프로젝트는 단순한 “인기있는 AI 리스트”가 아니라,
실무자가 실제로 맞닥뜨리는 구체적인 페인 포인트를 해결하는 솔루션입니다.

>This project is not just a list of trending AI tools — it solves real, practical pain points that professionals encounter.


<br>
<br>

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

<br>

We live in a world where new AI tools drop every single day.

But strangely, most people say things like:

> “Too many AIs… which one am I supposed to use?”
> “I have no idea which AI fits my work.”
> “I spend more time comparing tools than actually working.”

So the problem isn’t that good AIs don’t exist — it’s that there are way too many of them.

And that’s why we started this project.

>We asked:
“Can’t I just get the right AI for my situation without drowning in search tabs?”

From that question, we built an AI meta-recommendation platform that organizes, filters, and curates tools for you.
And that became Job-Fit AI Navigator.

<br>
<br>

## 🚀 주요 기능 (Features)
- **직무별 큐레이션 / Job-Based Curation**: 마케터, 개발자, 기획자, 디자이너 등 직군별 최적화된 AI를 분류합니다.
  > We classify AI tools optimized for marketers, developers, PMs, designers, HR, and more.
  
- **상황별 매칭 / Situation-Based Matching**: 리서치, 브레인스토밍, 보고서 작성, 디자인 생성, PPT 제작 등 “지금 이 상황”에 최적화된 AI를 자동 추천합니다.
  > Research, brainstorming, drafting, design, PPT creation — we match the AI that fits your current task.
  
- **워크플로우 레시피 제공 / Workflow Recipes**: 단일 AI 추천을 넘어, 여러 AI를 조합해 “최적의 AI 조합(Recipe)”을 제시합니다.
  ex) Perplexity → 해외 리서치, Claude → 보고서 초안, Gamma → PPT 자동 생성
  > We provide multi-AI workflows for complete tasks.
  ex) Perplexity → Research → Claude → Draft → Gamma → PPT
  
- **CSV 기반 추천 엔진 고도화 / CSV-Based Recommendation Engine** : 내부 DB를 기반으로 AI 정보를 관리합니다.
  새로운 AI 도구는 DB에 자동 추가되며, 적합하지 않은 도구는 비추천 기능을 통해 자동으로 제외됩니다.
  > A structured internal CSV database manages all AI info. New tools are added automatically; low-quality tools can be filtered out via feedback.
  
- **사용자 피드백 기반 자동 학습 / Feedback-Based Auto-Learning** : 👎 비추천 3회 → CSV DB에서 해당 AI 자동 삭제, 👍 새로운 AI 도구 입력 후 추천 → CSV DB에 자동 추가
  사용할수록 추천 품질이 좋아지는 구조입니다.
  >👎 3 downvotes → tool removed 👍 User-added tools → auto-added to the DB

<br>
<br>

## ⚙️ How It Works
<img width="1902" height="837" alt="image" src="https://github.com/user-attachments/assets/e6ec31b0-8aa8-4c27-8799-e1c49bfb2e32" />
## ⚙️ How It Works: System Architecture

Job-Fit AI Navigator는 **Streamlit 인터페이스**, **Gemini API(LLM)**, 그리고 **Google Spreadsheet(Cloud DB)**가 실시간으로 연동되는 **Self-Evolving System**입니다.
> The system operates as a **Self-Evolving System** integrating **Streamlit UI**, **Gemini API**, and **Google Spreadsheet** in real-time.

```mermaid
graph TD
    User((User))
    UI[Streamlit Web Interface]
    DB[(Google Cloud DB\nExcel/Sheets)]
    LLM[Google Gemini API]

    subgraph Input Phase
    DB -.->|Sync Options| UI
    User -->|1. Select via Sidebar| UI
    User -->|2. Direct Chat| UI
    end

    subgraph Processing Phase
    UI -->|3. Send Context| LLM
    LLM -->|4. Generate Response| UI
    end

    subgraph Evolution Phase (Core)
    User -->|5. Click 'Tool Mgmt'| UI
    UI -->|6. Request Extraction| LLM
    LLM -->|7. Extract Structured Data| UI
    UI -->|8. Update or Delete Row| DB
    end
<br>
<br>

🔍 1. 사용자 입력

자유롭게 텍스트로 입력하면 됩니다.

예: “나는 마케팅팀인데 이번 주 안에 광고 이미지랑 카피를 만들어야 해.”

> Just describe your task naturally. (Example: “I’m on the marketing team and need to create ad images and copy.”)

<br>

🧠 2. LLM이 입력을 구조화

Job: 마케터

Situation: 콘텐츠 제작

Output: 이미지 + 카피

>LLM classifies your input into Job, Situation, and Output.


<br>

🔎 3. CSV DB에서 필터링

직무 + 상황 + 결과물 기준으로
해당 상황에 맞는 AI 도구만 추출.

> We filter tools using the Job × Situation × Output structure.

<br>

🧩 4. 우선순위 스코어링

신뢰성

난이도

가격(무료/유료)

속도
이 요소를 기준으로 적합도 점수를 계산.

> We score tools based on reliability, complexity, speed, and price.

<br>

🔁 5. 사용자 피드백 반영

비추천 3회 → 자동 제거

추천된 새 도구 → 자동 추가
→ 시간이 지날수록 더 똑똑해지는 추천 엔진 완성.

> The more it's used, the smarter the system becomes.

<br>
<br>


## 📂 추천 목록 예시 (Preview)

| 상황 (Situation) | 추천 도구 (Tool) | 활용 팁 (Tip) |
| :--- | :--- | :--- |
| **해외 시장 리서치** | **Perplexity** | 출처가 명시된 답변을 제공하므로 팩트 체크에 유리합니다. |
| **사업 제안서 초안** | **Claude 3.5 Sonnet** | 논리적인 글쓰기와 문맥 파악 능력이 뛰어나 초안 작성에 탁월합니다. |
| **발표용 PPT 생성** | **Gamma** | 텍스트 개요만 넣으면 디자인된 슬라이드를 자동 생성합니다. |

*실제 추천 결과는 사용자 입력과 DB, 그리고 누적된 피드백에 따라 달라집니다.*
> Actual results depend on user input and the database.

<br>
<br>

## 🗂️ Database & Web Demo

CSV Database (Google Spreadsheet)
👉 https://docs.google.com/spreadsheets/d/176EoAIiDYnDiD9hORKABr_juIgRZZss5ApTqdaRCx5E/edit?gid=0#gid=0

웹 데모 (Streamlit Web Demo)
👉 https://job-fit-ai-navigator-dfpc8ttxmdtugtappucmjyb.streamlit.app/#job-fit-ai

<br>
<br>


## 🛠️ Next Level : Project Vision

Job-Fit AI Navigator는 단순한 큐레이션을 넘어, 사용자 피드백을 통해 스스로 진화하고 AI 도구를 직접 실행하는 '완전형 메타 AI 에이전트'를 지향합니다.
<br>
### 1. 자가 진화형 DB 및 동적 스코어링 (Self-Evolving DB & Dynamic Scoring)
> "데이터가 고이면 썩습니다. 우리는 살아 움직이는 AI 생태계를 구축합니다."

단순히 새로운 툴을 쌓아두는 것이 아니라, 데이터의 질(Quality)을 자동으로 관리하는 시스템을 구축합니다. <br>
* **사용자 피드백 루프 (RLHF 적용):** 사용자의 실제 선택과 평가(Click, Vote)를 가중치로 환산하여, 신뢰도가 높은 툴을 상단에 우선 노출합니다. <br>
* **스마트 퀄리티 게이트 (Automated Quality Gate):** 크롤링된 신규 AI 툴에 대해 `서버 응답 속도`, `무료 플랜 가용성`, `기능 명세 구체성` 등을 수치화하여 점수를 매깁니다. 기준 점수(Threshold) 미달인 '껍데기 AI'는 DB 진입 단계에서 자동으로 필터링됩니다. <br>
* **개인화 추천 알고리즘:** 사용자의 과거 조회 이력과 직무(Job) 데이터를 분석해, "다른 마케터들이 이 상황에서 가장 많이 결제한 툴"과 같은 맞춤형 제안을 제공합니다.

### 2. 실행 가능한 메타 인터페이스 (Actionable Meta-Interface)
> "추천받고, 이동하고, 가입하고... 귀찮으셨죠? 여기서 바로 실행하세요."

'추천'에서 끝나는 것이 아니라, Navigator 내부에서 해당 AI의 기능을 즉시 사용할 수 있는 **All-in-One 워크스페이스**로 확장합니다.<br>
* **API 통합 게이트웨이 (Unified API Gateway):** 주요 AI 툴(GPT, Claude, Midjourney, Perplexity 등)의 API를 연동하여, 사용자가 별도 사이트 이동 없이 Job-Fit Navigator 채팅창에서 바로 결과물을 받아볼 수 있게 합니다. <br>
* **AI 에이전트 워크플로우 (Agentic Workflow):**

    ```text
    User: "이번 프로젝트 기획안 초안 잡고 PPT까지 만들어줘."
    Navigator: (내부 처리) Perplexity(자료조사) → Claude(초안) → Gamma(PPT)
    Result: 사용자는 클릭 한 번으로 최종 PPT 파일만 다운로드.
    ```
    
## 🤝 기여하기 (Contribution)
여러분이 알고 있는 '꿀팁' AI 도구가 있다면 제보해 주세요!
>If you know a hidden-gem AI tool, tell us!

<br>

1. 이 저장소를 **Star(⭐️)** 눌러주세요. / Please Star (⭐️) this repository.
2. `Issues` 탭에 새로운 AI 도구 제안하거나, `Pull Request`를 보내주세요. / Suggest tools via the Issues tab or Pull Requests are welcome!



“AI를 잘 쓰는 사람”보다,
“AI를 잘 골라 쓰는 사람”이 경쟁력이 되는 시대.

**Job-Fit AI Navigator**가 그 사이를 이어주는 브릿지가 되겠습니다.

---
Created by [2025-2 인간-인공지능협업제품서비스설계 / 3팀]
