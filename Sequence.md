sequenceDiagram
    autonumber
    actor User as 👤 사용자 (User)
    participant Web as 🖥️ Streamlit Web
    participant DB as 📂 Google Drive (DB)
    participant AI as ✨ Gemini API

    Note over User, AI: 1. 초기화 및 메뉴 로딩 (Initialization)
    User->>Web: 사이트 접속
    Web->>DB: 최신 AI 도구 리스트 요청 (Fetch Data)
    DB-->>Web: 직무(Job), 상황(Situation) 데이터 반환
    Web-->>User: 사이드바 옵션 및 UI 표시

    Note over User, AI: 2. 추천 서비스 (Recommendation Service)
    alt 빠른 메뉴 선택 (Quick Menu)
        User->>Web: 직무/상황 선택 후 질문 생성
    else 직접 질문 (Direct Chat)
        User->>Web: 자연어로 고민 입력
    end

    Web->>AI: 프롬프트 + DB 데이터 전송
    AI-->>Web: 최적의 AI 도구 및 팁 생성
    Web-->>User: 추천 결과 화면 표시

    Note over User, AI: 3. 자가 진화 시스템 (Self-Evolving Loop)
    opt 사용자 피드백 (Feedback)
        
        alt 👍 도구 관리 및 추가 (Add Tool)
            User->>Web: '이 도구 추가/관리' 버튼 클릭
            Web->>AI: 대화 문맥(Context)에서 정보 추출 요청
            AI-->>Web: 구조화된 데이터 반환 (JSON: 이름, 직무, 링크 등)
            Web->>DB: 새로운 AI 도구 자동 추가 (Update Row)
            DB-->>Web: 업데이트 완료 신호
            Web-->>User: "DB에 반영되었습니다" 알림
        
        else 👎 비추천 (Dislike)
            User->>Web: '비추천' 버튼 클릭
            Web->>DB: 해당 도구 비추천 카운트 증가 (+1)
            
            rect rgb(255, 200, 200)
                Note right of DB: 자동 삭제 로직
                DB->>DB: 누적 카운트 확인
                alt 카운트 >= 3회
                    DB->>DB: 해당 도구 영구 삭제 (Delete Row)
                end
            end
            Web-->>User: 피드백 반영 완료 알림
        end
    end