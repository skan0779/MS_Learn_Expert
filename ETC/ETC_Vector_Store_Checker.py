import os
from openai import AzureOpenAI
from dotenv import load_dotenv

# 개인 설정
vs_name = "MS Learn Expert Vector Store V1"

# 환경변수 로드
load_dotenv(dotenv_path="/Users/skan/Desktop/AI_Prototyping_Team/MS_Azure_RAG/.env")

# Client 생성
client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)

# Data Files ID 반환
data_files_response = client.files.list()
data_files_ids = [data_file.id for data_file in data_files_response.data]

# Vector Store ID 반환
def get_or_create_vector_store(client, vs_name):
    try:
        response = client.beta.vector_stores.list()
        vector_store_info = [(vector_store.name, vector_store.id) for vector_store in response.data]
        existing_vector_store_id = next((vector_store_id for name, vector_store_id in vector_store_info if name == vs_name), None)

        if existing_vector_store_id:
            return existing_vector_store_id
        else:
            new_vector_store = client.beta.vector_stores.create(name=vs_name)
            new_vector_store_id = new_vector_store.id
            return new_vector_store_id
    except Exception as e:
        return None
vector_store_id = get_or_create_vector_store(client, vs_name)

# Vector Store Files 반환
def get_all_vector_store_files(client, vector_store_id):
    try:
        all_files = []
        next_after = None
        limit = 100

        while True:
            if next_after:
                response = client.beta.vector_stores.files.list(vector_store_id=vector_store_id, limit=limit, after=next_after)
            else:
                response = client.beta.vector_stores.files.list(vector_store_id=vector_store_id, limit=limit)
            all_files.extend(response.data)
            if response.has_more:
                next_after = response.data[-1].id
            else:
                break
        return all_files
    except Exception as e:
        print(f"Error retrieving all vector store files: {str(e)}")
        return []
vector_store_files = get_all_vector_store_files(client, vector_store_id)
vector_store_ids = [vector_file.id for vector_file in vector_store_files]

# Vector Store Status Failed 경우
count_A = 0
checker = set()
for vector_file in vector_store_files:
    if vector_file.status == 'failed':
        checker.add(vector_file.id)
        count_A += 1

# Data Files 에 있지만 Vector Store 에 없는 경우
count_B = 0
for data_file_id in data_files_ids:
    if data_file_id not in vector_store_ids:
        checker.add(data_file_id)
        count_B += 1

# Data Files 파일 제거
count_C = 0
checker = list(checker)
for check in checker:
    response = client.files.list()
    data_file_info = [(data_file.filename, data_file.id) for data_file in response.data]
    check_name = next((filename for filename, file_id in data_file_info if file_id == check), None)

    print(f"""
          File Name : {check_name}
          File ID : {check}""")
    try:
        deleted_vector_store_file = client.files.delete(
            file_id = check
        )
        count_C += 1
        print("          Data File Delete Complete")
    except Exception as e:
        print(f"          Error in deleting Data File: {str(e)}")

print(f"""
        ########################### Checking Complete ###############################
        Vector Store ID : {vector_store_id}

        Data Files : {len(data_files_ids)}
        Vector Store : {len(vector_store_ids)}

        Vector Store Status Failed : {count_A}
        Data Files not in Vector Store : {count_B}

        Delete Target : {len(checker)}
        Data Files Deleted : {count_C}
        ############################################################################
    """)
