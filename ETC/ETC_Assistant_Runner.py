import os
import time
from openai import AzureOpenAI
from dotenv import load_dotenv

# 개인 설정
assistant_name = "MS Learn Expert Assistant V1"
question = "Azure AI Studio 사용법을 간략히 설명해 주세요"

# 환경변수 로드
load_dotenv(dotenv_path = "/Users/skan/Desktop/AI_Prototyping_Team/MS_Azure_RAG/.env")

# Client 생성
client = AzureOpenAI(
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key = os.getenv("AZURE_OPENAI_API_KEY"),
    api_version = os.getenv("AZURE_OPENAI_API_VERSION")
)

# Thread 생성
thread = client.beta.threads.create()

# Message 생성
message = client.beta.threads.messages.create(
    thread_id = thread.id,
    role = "user",
    content = question
)

# Assistant ID 반환 함수
def get_or_create_assistant(client, assistant_name):
    try:
        response = client.beta.assistants.list()
        assistant_info = [(assistant.name, assistant.id) for assistant in response.data]
        existing_assistant = next((assistant_id for name, assistant_id in assistant_info if name == assistant_name), None)
        return existing_assistant
    except Exception as e:
        print(f"Error in retrieving Assistant ID: {str(e)}")
        return None
    
# Assistant 생성
assistant_id = get_or_create_assistant(client, assistant_name)

# Assistant 실행
run = client.beta.threads.runs.create(
    thread_id = thread.id,
    assistant_id = assistant_id
)

# 실행 상태 체크
while run.status in ['queued', 'in_progress', 'cancelling']:
    time.sleep(1)
    run = client.beta.threads.runs.retrieve(
        thread_id = thread.id,
        run_id = run.id
    )

# Message 출력
if run.status == 'completed':
    # 메시지 목록 가져오기
    thread_messages = client.beta.threads.messages.list(thread_id=thread.id)
    
    for message in thread_messages.data:
        # 메시지가 'assistant' 역할을 가진 경우만 출력
        if message.role == 'assistant':
            # 'content'에서 'value' 값을 추출하여 출력
            for content_block in message.content:
                if hasattr(content_block.text, 'value'):
                    print(content_block.text.value)

elif run.status == 'requires_action':
    print("The assistant requires additional actions to complete.")

else:
    print(f"Run status: {run.status}")

