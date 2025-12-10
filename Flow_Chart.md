```mermaid
graph LR
    %% 스타일 정의
    classDef startend fill:#f9f,stroke:#333,stroke-width:2px,color:black,rx:10,ry:10
    classDef process fill:#e1f5fe,stroke:#0277bd,stroke-width:1px,color:black
    classDef decision fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:black,rhombus
    classDef db fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,stroke-dasharray: 3 3,color:black,cylinder
    classDef api fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:black,rect

    %% 1단계: 접속 및 입력
    subgraph Step1 ["1. 접속 및 입력 (Input)"]
        direction TB
        Start(["Start"]):::startend
        InitDB[("DB Load")]:::db
        ShowUI["Web UI"]:::process
        InputChoice{"입력 방식"}:::decision
        QuickMenu["빠른 메뉴"]:::process
        DirectChat["직접 질문"]:::process
    end

    %% 2단계: 처리 및 결과
    subgraph Step2 ["2. AI 처리 (Processing)"]
        direction TB
        GenPrompt["프롬프트 생성"]:::process
        GeminiAPI{{"Gemini API"}}:::api
        ShowResult["결과 화면"]:::process
    end

    %% 3단계: 피드백 및 DB 진화
    subgraph Step3 ["3. DB 진화 (Evolution)"]
        direction TB
        FeedbackChoice{"피드백"}:::decision
        
        %% 추가 경로
        PathAdd["👍 추천"]
        ReqExtract["문맥 추출"]:::process
        UpdateDBAdd[("DB 추가")]:::db

        %% 삭제 경로
        PathDislike["👎 비추천"]
        UpdateDBDislike[("카운트 +1")]:::db
        CheckCount{"3회 누적?"}:::decision
        DeleteRow[("DB 삭제")]:::db
    end

    End(["End"]):::startend

    %% 연결선 (흐름)
    Start --> InitDB
    InitDB --> ShowUI
    ShowUI --> InputChoice
    
    InputChoice -- "선택" --> QuickMenu
    InputChoice -- "채팅" --> DirectChat
    
    QuickMenu --> GenPrompt
    DirectChat --> GenPrompt
    
    GenPrompt --> GeminiAPI
    GeminiAPI --> ShowResult
    ShowResult --> FeedbackChoice

    %% 피드백 루프 연결
    FeedbackChoice -- "좋아요" --> PathAdd
    PathAdd --> ReqExtract --> UpdateDBAdd --> End

    FeedbackChoice -- "싫어요" --> PathDislike
    PathDislike --> UpdateDBDislike --> CheckCount
    
    CheckCount -- "Yes" --> DeleteRow --> End
    CheckCount -- "No" --> End