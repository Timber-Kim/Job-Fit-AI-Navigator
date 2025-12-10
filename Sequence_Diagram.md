```mermaid
graph TD
    %% 스타일 정의 (색상 및 모양)
    classDef startend fill:#f9f,stroke:#333,stroke-width:2px,color:black,rx:15,ry:15;
    classDef process fill:#e1f5fe,stroke:#0277bd,stroke-width:1px,color:black;
    classDef decision fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:black,rhombus;
    classDef db fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,stroke-dasharray: 3 3,color:black,cylinder;
    classDef api fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:black,rect;

    %% 노드 정의 (콜론 제거 완료)
    Start([시작: 사용자 웹 접속]):::startend
    InitDB[(Google Drive DB:<br>초기 데이터 로드)]:::db
    ShowUI[Streamlit 웹 UI 표시]

    InputChoice{입력 방식 선택}:::decision
    QuickMenu[빠른 메뉴 선택<br>직무/상황/결과물]:::process
    DirectChat[직접 질문 입력<br>자연어]:::process
    
    GenPrompt[프롬프트 생성 및 전송]:::process
    GeminiAPI{{Gemini API:<br>의도 분석 및 추천 결과 생성}}:::api
    ShowResult[결과 화면 표시]

    FeedbackChoice{사용자 피드백}:::decision
    
    %% 도구 추가 프로세스
    PathAdd[👍 도구 관리/추천 클릭]
    ReqExtract[Gemini에 문맥 추출 요청]:::process
    GeminiExtract{{Gemini API:<br>대화 문맥에서 JSON 데이터 추출}}:::api
    UpdateDBAdd[(DB 업데이트:<br>새 도구 데이터 추가)]:::db

    %% 도구 비추천 프로세스
    PathDislike[👎 비추천 클릭]
    UpdateDBDislike[(DB 업데이트:<br>비추천 카운트 +1)]:::db
    CheckCount{누적 비추천<br>3회 도달?}:::decision
    DeleteRow[(DB 업데이트:<br>해당 도구 영구 삭제)]:::db
    KeepRow[도구 유지]

    End([끝: 대기 상태]):::startend

    %% 연결선 정의
    Start --> InitDB
    InitDB --> ShowUI
    ShowUI --> InputChoice
    
    InputChoice -- 빠른 메뉴 --> QuickMenu
    InputChoice -- 직접 질문 --> DirectChat
    
    QuickMenu --> GenPrompt
    DirectChat --> GenPrompt
    
    GenPrompt --> GeminiAPI
    GeminiAPI --> ShowResult
    
    ShowResult --> FeedbackChoice

    FeedbackChoice -- "만족 (👍)" --> PathAdd
    PathAdd --> ReqExtract
    ReqExtract --> GeminiExtract
    GeminiExtract --> UpdateDBAdd
    UpdateDBAdd --> End

    FeedbackChoice -- "불만족 (👎)" --> PathDislike
    PathDislike --> UpdateDBDislike
    UpdateDBDislike --> CheckCount
    
    CheckCount -- Yes (삭제) --> DeleteRow
    CheckCount -- No (유지) --> KeepRow
    
    DeleteRow --> End
    KeepRow --> End