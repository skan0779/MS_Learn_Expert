# Data Files 
# - Vector Store 공용 Storage, 본 코드에서는 Data Files 기준 공통 업로드된 파일들의 중복을 금지하였음 -> 단일 Vector Store 사용 체계
# - 필요 시, 각 vector store 별 중복 금지 설정 필요함 -> file_id 기준 중복 확인으로 변경 필요

import math
import time
import json
import logging
import os
from datetime import datetime
from dotenv import load_dotenv
from openai import AzureOpenAI

# 개인 설정
project_path = "/Users/skan/Desktop/AI_Prototyping_Team/MS_Azure_RAG"
data_path = "/Users/skan/Desktop/AI_Prototyping_Team/MS_Azure_RAG/Preprocessed_PDF"
assistant_name = "MS Learn Expert Assistant V1"
model_name = "gpt-4o"
vs_name = "MS Learn Expert Vector Store V1"
system_message = """
    You are a specialized assistant with in-depth knowledge in Microsoft technologies, trained to provide expert guidance on topics covered in MS Learn PDF documents.
    Your role is to assist users by drawing from specific details within these documents to answer questions about Azure, AI, cloud services, and other relevant Microsoft tools and best practices.
    Answer concisely, provide actionable insights, and cite concepts or recommendations directly related to the MS Learn materials wherever applicable.
    If a user query is outside the scope of these documents, politely inform the user of your focus on MS Learn content. 
    When generating your answer, please explain your thoughts in detail, step by step, using the content provided.
    If the user's question relates to Microsoft service, include official document link for that service in the last sentense of your response.
    If you don't know the answer, just say you don't know.
    Please answer in Korean.
    """
batch = 10
chunk_size = 1500
chunk_overlap = 100

# 로깅 설정
if not os.path.exists(f'{project_path}/Log'):
    os.makedirs(f'{project_path}/Log')

log_filename = f'{project_path}/Log/create_vector_store_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Data Files 반환 함수
def get_existing_vector_store_files(client, vector_store_id):
    try:
        # response = client.beta.vector_stores.files.list(vector_store_id = vector_store_id)
        response = client.files.list()
        return {file.filename for file in response.data}
    except Exception as e:
        logger.error(f"Error retrieving Data Files: {str(e)}")
        return set()

# Assistant ID 반환 함수
def get_or_create_assistant(client, assistant_name, model_name, system_message):
    try:
        response = client.beta.assistants.list()
        assistant_info = [(assistant.name, assistant.id) for assistant in response.data]
        existing_assistant = next((assistant_id for name, assistant_id in assistant_info if name == assistant_name), None)

        if existing_assistant:
            logger.info(f"Retrieving assistant ID: {existing_assistant}")
            return existing_assistant
        else:
            new_assistant = client.beta.assistants.create(
                name=assistant_name,
                model=model_name,
                instructions=system_message,
                tools=[{"type": "file_search"}],
            )
            logger.info(f"Creating assistant ID: {new_assistant.id}")
            return new_assistant.id
    except Exception as e:
        logger.error(f"Error in creating or retrieving Assistant ID: {str(e)}")
        return None

# Vector Store ID 반환 함수
def get_or_create_vector_store(client, vs_name):
    try:
        response = client.beta.vector_stores.list()
        vector_store_info = [(vector_store.name, vector_store.id) for vector_store in response.data]
        existing_vector_store_id = next((vector_store_id for name, vector_store_id in vector_store_info if name == vs_name), None)

        if existing_vector_store_id:
            logger.info(f"Retrieving vector store ID: {existing_vector_store_id}")
            return existing_vector_store_id
        else:
            new_vector_store = client.beta.vector_stores.create(name = vs_name)
            new_vector_store_id = new_vector_store.id
            logger.info(f"Creating vector store ID: {new_vector_store_id}")
            return new_vector_store_id
    except Exception as e:
        logger.error(f"Error in creating or retrieving Vector Store ID: {str(e)}")
        return None

# 메인 함수 정의
def main():
    # 환경변수 설정
    load_dotenv(dotenv_path=f"{project_path}/.env")

    # 클라이언트 생성
    client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
    )

    # Assistant 생성
    assistant_id = get_or_create_assistant(client, assistant_name, model_name, system_message)
    assistant = client.beta.assistants.retrieve(assistant_id)

    # Vector Store 생성
    vector_store_id = get_or_create_vector_store(client, vs_name)

    # 파일 준비
    folder_path = data_path
    file_paths = [os.path.join(folder_path, f) for f in os.listdir(folder_path) 
                  if os.path.isfile(os.path.join(folder_path, f)) and f.lower().endswith('.pdf')]

    # 중복 파일 제거
    existing_files = get_existing_vector_store_files(client, vector_store_id)
    logger.info(f"Retrieving Data Files: {existing_files}")
    new_files = [
        open(path, "rb") for path in file_paths
        if os.path.basename(path) not in existing_files and path.lower().endswith('.pdf')
    ]
    if not new_files:
        logger.info("No new Data Files to upload")
        print("""
                ######################## Upload Complete ###############################
                    No New Data Files to Upload
                ########################################################################
            """)
        return

    # 파일 업로드 함수
    def batch_upload_files(client, vector_store_id, file_streams, batch_size=batch, delay=30, max_retries=2):
        total_files = len(file_streams)
        num_batches = math.ceil(total_files / batch_size)

        for i in range(num_batches):
            start_idx = i * batch_size
            end_idx = min((i + 1) * batch_size, total_files)
            current_batch = file_streams[start_idx:end_idx]
            logger.info(f"Uploading batch {i + 1}/{num_batches} (Files {start_idx + 1} to {end_idx})")
            
            try:
                file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
                    vector_store_id=vector_store_id,
                    files=current_batch,
                    chunking_strategy={
                        "type": "static",
                        "static": {
                            "max_chunk_size_tokens": chunk_size,
                            "chunk_overlap_tokens": chunk_overlap
                        }
                    }
                )
                logger.info(f"Batch {i + 1} upload complete. Status: {file_batch.status}")
            except Exception as e:
                logger.error(f"Error uploading batch {i + 1}: {str(e)}")
                logger.info(f"Waiting for {delay} seconds to retry...")
                time.sleep(delay)

    # 파일 업로드
    batch_upload_files(client, vector_store_id, new_files)

    # Assistant 업데이트
    assistant = client.beta.assistants.update(
        assistant_id=assistant.id,
        tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}},
    )
    logger.info(f"Updated assistant {assistant.id} with vector store {vector_store_id}")

    # 결과 출력
    print(f"""
        ######################## Create & Retrieve Complete ###############################
        Vector Store ID : {vector_store_id}
        Assistant ID : {assistant.id}
        ###################################################################################
    """)

    # Stream 종료
    for file_stream in new_files:
        file_stream.close()

# 메인 함수 실행
if __name__ == "__main__":
    main()
