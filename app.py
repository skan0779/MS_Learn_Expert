import os
import time
import gradio as gr
from openai import AzureOpenAI
import re

# 개인 설정
routing_assistant_id = "asst_AWD2G1DNgx6B6DjIisu4liZD"
normal_assistant_id = "asst_wVAtF6vw0nxwjcd9PD8NVph2"

# 로그인 설정
auth_list = [
    ('user1','1234'),
    ('user2','2345'),
    ('user3','3456'),
    ('user4','4567'),
    ('user5','5678')
]

# 전역 변수
assistant_cache = {}
auth_cache = {}

# Client 생성
client = AzureOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version=os.environ["AZURE_OPENAI_API_VERSION"]
)

# 로그인 함수 (캐싱처리)
def login(username, password):
    # 사용중인 ID 차단
    if username in auth_cache:
        return False, "다른 사용자가 사용중인 ID 입니다, 다른 ID를 입력해 주세요."

    # 로그인 인증
    for user, pwd in auth_list:
        if username == user and password == pwd:
            auth_cache[username] = True
            return True, ""
    
    return False, "잘못된 ID 또는 PW 입니다, 다시 입력해 주세요."

# 로그인 래퍼 함수
def custom_auth(username, password):
    result, message = login(username, password)
    print(message)

    if not result:
        return False
    return True

# 페이지 로드 함수
def login_page(request: gr.Request):
    # 사용자 ID 반환
    username = request.username
    return f"{username}"

# 로그아웃 함수 (캐싱처리)
def logout(login_user):
    # 캐시 삭제
    if login_user in auth_cache:
        del auth_cache[login_user]

# Assistant ID 반환 함수 (캐싱처리)
def get_assistant_id(client, assistant_name):
    # 캐시 확인
    if assistant_name in assistant_cache:
        return assistant_cache[assistant_name]
    # Assistant ID 불러오기
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
    # thread 생성
    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=question
    )
    # assistant 질문
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
    # state 초기화
    if state is None:
        state = {}

    # thread 생성 및 저장
    thread = client.beta.threads.create()
    state["current_thread_id"] = thread.id

    # 채팅박스 초기화
    chatbot = []

    # assistant name 초기화
    assistant_name_input = "MS Learn Expert Assistant V1"

    return chatbot, assistant_name_input, state["current_thread_id"]

# Gradio UI 구성 함수
def create_gradio_ui_stream():
    with gr.Blocks() as demo:
        # 제목 구성
        gr.Markdown("## MS Learn Expert")

        # Session 관리
        state = gr.State(value={"current_thread_id": None})

        # UI 구성
        with gr.Row():
            with gr.Column(scale=1):
                assistant_name_input = gr.Textbox(label="Assistant Name", value="MS Learn Expert Assistant V1")
                thread_id_label = gr.Textbox(label="Thread ID", value="None", interactive=False)
                question_input = gr.Textbox(label="Question", lines=5, placeholder="Enter your question here...")
                with gr.Row():
                    submit_button = gr.Button("Run")
                    new_chat_button = gr.Button("Start a new Chat")
                login_user = gr.Textbox(label="User ID", value=None, interactive=False)  
                with gr.Row():
                    logout_button = gr.Button("Logout")
                    home_button = gr.Button("Home", link="/logout")
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(label="Chatbox", height=830)

        # Event 함수 : run 버튼
        submit_button.click(
            fn=ask_question_streaming,
            inputs=[state, chatbot, assistant_name_input, question_input],
            outputs=[chatbot, state, thread_id_label],
            concurrency_limit=10, 
            queue=True
        )
        
        # Event 함수 : start a new chat 버튼
        new_chat_button.click(
            fn=new_chat,
            inputs=[state], 
            outputs=[chatbot, assistant_name_input, thread_id_label],
            concurrency_limit=10, 
            queue=True
        )

        # Event 함수 : logout 버튼
        logout_button.click(
            fn=logout,
            inputs=[login_user],
            outputs=[login_user],
            concurrency_limit=10, 
            queue=True
        )

        # 로그인 유저 ID 반환
        demo.load(login_page, None, login_user)

    return demo

# Gradio 앱 실행
create_gradio_ui_stream().queue(max_size=10).launch(
    auth=custom_auth,
    # favicon_path="/Users/skan/Desktop/AI_Prototyping_Team/MS_Azure_RAG/icon/microsoft.png",
    share=True, 
    server_name="0.0.0.0", 
    server_port=7860,
    max_threads=5
    )
