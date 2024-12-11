import os
from dotenv import load_dotenv
from openai import AzureOpenAI

# 환경 변수
load_dotenv(dotenv_path="/Users/skan/Desktop/AI_Prototyping_Team/MS_Azure_RAG/.env")

# Client 생성
client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)

# Assistant 생성 및 ID 반환 함수
def get_or_create_assistant(client, assistant_name, model_name, system_message):
    try:
        response = client.beta.assistants.list()
        assistant_info = [(assistant.name, assistant.id) for assistant in response.data]
        existing_assistant = next((assistant_id for name, assistant_id in assistant_info if name == assistant_name), None)

        if existing_assistant:
            return existing_assistant
        else:
            new_assistant = client.beta.assistants.create(
                name=assistant_name,
                model=model_name,
                instructions=system_message,
            )
            return new_assistant.id
    except Exception as e:
        return None

# Router Assistant 생성
router_assistant_name = "MS Learn Routing Assistant"
router_assistant_model = "gpt-4o-mini"
router_assistant_message = """
    You are a classifier assistant.
    Your task is to determine if a given user question is related to Microsoft services, such as Azure, Microsoft Cloud, Microsoft Copliot, Microsoft Copliot Studio, Microsoft Industry Clouds, Fabric, Graph, Teams, OpenAPI, Power Apps, Power BI, PowerShell, Semantic Kernel, Visual Studio, OpenAI or any other Microsoft product or service.
    Please respond with only "True" if the question is related to Microsoft services or "False" if it is unrelated.
    Don't provide any additional explanation or context in your response.
"""
router_assistant_id = get_or_create_assistant(client,router_assistant_name, router_assistant_model, router_assistant_message)

# Normal Assistant 생성
normal_assistant_name = "MS Learn Normal Assistant"
normal_assistant_model = "gpt-4o-mini"
normal_assistant_message = """
    If you don't know the answer, just say you don't know.
    Please answer in korean.
"""
normal_assistant_id = get_or_create_assistant(client, normal_assistant_name, normal_assistant_model, normal_assistant_message)

# 출력
print(f"""
      ########################### Assistant Creation Complete ##############################
      Router Assistant ID : {router_assistant_id}
      Normal Assistant ID : {normal_assistant_id}
      #############################################################################
      """)