import os
import time
import gradio as gr
from openai import AzureOpenAI
from dotenv import load_dotenv
import re

# 개인 설정 (Step6 출력 참고)
routing_assistant_id = "asst_AWD2G1DNgx6B6DjIisu4liZD"
normal_assistant_id = "asst_wVAtF6vw0nxwjcd9PD8NVph2"

# 환경 변수
load_dotenv(dotenv_path="/Users/skan/Desktop/AI_Prototyping_Team/MS_Azure_RAG/.env")

# 전역 변수
assistant_cache = {}

# Client 생성
client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)

# Assistant ID 반환 함수 (캐싱처리)
def get_assistant_id(client, assistant_name):
    if assistant_name in assistant_cache:
        return assistant_cache[assistant_name]
    
    try:
        response = client.beta.assistants.list()
        assistant_info = [(assistant.name, assistant.id) for assistant in response.data]
        existing_assistant = next((assistant_id for name, assistant_id in assistant_info if name == assistant_name), None)
        if existing_assistant:
            assistant_cache[assistant_name] = existing_assistant
        return existing_assistant
    except Exception as e:
        return None

# Routing 함수 ("True" or "False")
def routing(client, thread_id, question):
    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=question
    )

    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=routing_assistant_id
    )

    while run.status in ['queued', 'in_progress', 'cancelling']:
        time.sleep(0.3)
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id
        )

    if run.status == 'completed':
        thread_messages = client.beta.threads.messages.list(thread_id=thread_id)
        for message in thread_messages.data:
            if message.role == 'assistant':
                response_text = "".join([content.text.value for content in message.content if hasattr(content, 'text')])
                print(f"Routing Type : {response_text}")
                return response_text
    return "True"

# Assistant 질문 함수
def ask_question_streaming(state, chatbot, assistant_name, question):
    # 상태 출력
    print(f"State : {state}")

    # 상태 확인 및 초기화
    if state is None:
        state = {}

    if "current_thread_id" not in state:
        state["current_thread_id"] = None

    current_thread_id = state.get("current_thread_id", None)

    # Thread 생성 또는 기존 Thread ID 재사용
    if current_thread_id is None:
        thread = client.beta.threads.create()
        current_thread_id = thread.id
        state["current_thread_id"] = current_thread_id
    else:
        thread = client.beta.threads.retrieve(thread_id=current_thread_id)

    # 사용자 질문 추가
    client.beta.threads.messages.create(
        thread_id=current_thread_id,
        role="user",
        content=question
    )

    # Routing 결과 확인 (출력에서 제외)
    routing_question = routing(client, current_thread_id, question)
    assistant_id = get_assistant_id(client, assistant_name) if routing_question == "True" else normal_assistant_id

    # Assistant 실행
    run = client.beta.threads.runs.create(
        thread_id=current_thread_id,
        assistant_id=assistant_id
    )

    # 실행 상태 모니터링
    while run.status in ['queued', 'in_progress', 'cancelling']:
        time.sleep(0.3)
        run = client.beta.threads.runs.retrieve(
            thread_id=current_thread_id,
            run_id=run.id
        )

    # 답변 생성
    if run.status == 'completed':
        thread_messages = client.beta.threads.messages.list(thread_id=current_thread_id)
        response = ""
        full_chatbot = chatbot.copy()

        for message in thread_messages.data:
            if message.role == 'assistant':
                for content_block in message.content:
                    if hasattr(content_block.text, 'value'):
                        # 출력 전처리
                        full_char = content_block.text.value
                        full_char = re.sub(r'【\d+:\d+†source】', '', full_char)
                        full_char = re.sub(r'【\d+†source】', '', full_char)
                        full_char = re.sub(r'【\d+:\d+†link】', '', full_char)
                        full_char = re.sub(r'【\d+†link】', '', full_char)
                        # 출력 Streaming
                        for char in full_char:
                            response += char
                            updated_chatbot = full_chatbot + [(question, response.strip())]
                            yield updated_chatbot, state, current_thread_id
                            time.sleep(0.003)
                    return
        return

    # 기타 상태 처리
    elif run.status == 'requires_action':
        yield chatbot + [(question, "The assistant requires additional actions to complete.")], state, current_thread_id
    else:
        yield chatbot + [(question, f"Run status: {run.status}")], state, current_thread_id
    return

# 새 채팅 함수
def new_chat(state):
    # state가 None이면 빈 딕셔너리로 초기화
    if state is None:
        state = {}

    # 새로운 thread 생성
    thread = client.beta.threads.create()

    # current_thread_id에 새로 생성된 thread의 ID 저장
    state["current_thread_id"] = thread.id

    # 채팅 박스를 초기화
    chatbot = []

    # assistant_name 초기화 (필요시)
    assistant_name_input = "MS Learn Expert Assistant V1"  # 혹은 다른 초기 값

    return chatbot, assistant_name_input, state["current_thread_id"]

# Gradio UI 구성 함수
def create_gradio_ui_stream():
    with gr.Blocks() as demo:
        gr.Markdown("## MS Learn Expert")

        state = gr.State(value={"current_thread_id": None})

        with gr.Row():
            with gr.Column(scale=1):
                assistant_name_input = gr.Textbox(label="Assistant Name", value="MS Learn Expert Assistant V1")
                thread_id_label = gr.Textbox(label="Thread ID", value="None", interactive=False)
                question_input = gr.Textbox(label="Question", lines=5, placeholder="Enter your question here...")
                submit_button = gr.Button("Run")
                new_chat_button = gr.Button("Start a new Chat")

            with gr.Column(scale=3):
                chatbot = gr.Chatbot(label="Chatbox", height=830)

        submit_button.click(
            fn=ask_question_streaming,
            inputs=[state, chatbot, assistant_name_input, question_input],
            outputs=[chatbot, state, thread_id_label]
        )
        
        new_chat_button.click(
            fn=new_chat,
            inputs=[state], 
            outputs=[chatbot, assistant_name_input, thread_id_label]
        )

    return demo

# Gradio 앱 실행
create_gradio_ui_stream().launch(share=True)
