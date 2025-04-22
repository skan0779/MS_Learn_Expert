# MS_Learn_Document_Agent
MS 공식 문서 전문 Agent

1. Main Function
    - 최신 공식 문서를 기반한 빠른 답변 제공
    - 답변에 참고한 PDF 및 PDF Link 제공
    - 질문에 해당하는 서비스의 공식문서 사이트 URL 제공
  
2. Service stack
    - [Azure OpenAI Service](https://www.notion.so/Azure-OpenAI-Service-1bc7189c026b80c1bc16dece924dea16?pvs=21) : Thread, Model
    - [Azure AI Foundry](https://www.notion.so/Azure-AI-Foundry-1ad7189c026b8098a071fbdceecbe997?pvs=21)  : Assistant, Vector Store (File Search), Data Files
    - [Azure Container Registry](https://www.notion.so/Azure-Container-Registry-1ae7189c026b8099ad93d991c9c52da7?pvs=21) : Docker Image Repository
    - [Azure Functions](https://www.notion.so/Azure-Functions-1b27189c026b80609dbceee86db47b2f?pvs=21)  : Deployment
  
3. File Search Data (RAG)
    - MS Learn 사이트에 있는 Product 공식문서 (PDF) → https://learn.microsoft.com/pdf?url=https%3A%2F%2Flearn.microsoft.com%2Fen-us%2Fazure%2Fprivate-link%2Ftoc.json
    - MS Learn 사이트 →  https://learn.microsoft.com/en-us/docs/
    - Target Product →  Azure, Microsoft Cloud, Microsoft Copliot, Microsoft Copliot Studio, Microsoft Industry Clouds, Fabric, Graph, Teams, OpenAPI, 등
    - Total Data → 614개, 32GB
  
4. 데이터 수집
    - MS Learn 사이트 내 PDF 다운로드 버튼이 있는 모든 Leaf URL 추출 → (예시) https://learn.microsoft.com/ko-kr/azure/ai-studio/
    - Leaf URL에서 PDF URL 추출 → (예시) https://learn.microsoft.com/pdf?url=https%3A%2F%2Flearn.microsoft.com%2Fko-kr%2Fazure%2Fai-studio%2Ftoc.json
    - 모든 PDF 다운로드 (Local PC)
  
5. 데이터 전처리
    - PDF 파일 전처리 (Token size: 5,000,000 이하, File size: 500MB 이하가 되도록 파일 분할)
  
6. 데이터 업로드
    - Model 배포
    - Vector Store 생성
    - Data Files 파일 업로드
    - Vector Sore 임베딩 (text-embedding-3-large)
    - Assistant 생성 및 Vector Store 할당
    - File Search 및 Vector Store 예상 비용 확인 (0.13/1000000 per token, 0.1 per GB)
  
7. Routing 구현
    - Router Assistant 생성 (MS 서비스에 관련된 질문인지 판단)
    - Normal Assistant 생성 (일반 유형의 질문 담당)
  
8. 서비스 구현
    - 출력 텍스트 후처리 (특정 문자 제거)
    - Router Assistant 사용자 질문 의도분석 (기존 thread 공유)
    - 새 채팅 기능 추가 (신규 thread 생성 및 기존 message 삭제)
    - 출력 Stream (yield 반환으로 chatbot 업데이트)
    - 사용자별 Session 관리 및 병렬 처리 (State, Queue, concurrency)
    - 로그인 기능 추가 (동시 접속 제한 : 10명)
    - Gradio UI 구성
