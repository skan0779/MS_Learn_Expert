import os
from openai import AzureOpenAI
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv(dotenv_path = "/Users/skan/Desktop/AI_Prototyping_Team/MS_Azure_RAG/.env")

# Client 생성
client = AzureOpenAI(
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key = os.getenv("AZURE_OPENAI_API_KEY"),
    api_version = os.getenv("AZURE_OPENAI_API_VERSION")
)
response = client.files.list()
data_files_ids = [file.id for file in response.data]

for data_file_id in data_files_ids:
    deleted_vector_store_file = client.files.delete(
        file_id = data_file_id
    )
    print(f"File Deleted : {data_file_id}")

print(f"""
        ######################## Delete Complete ###############################
            Total {len(data_files_ids)} files have been deleted
        ########################################################################
    """)