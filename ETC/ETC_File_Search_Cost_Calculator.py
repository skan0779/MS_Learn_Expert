import os
import fitz
import tiktoken
from typing import Tuple, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

# 토큰 수 계산
def num_tokens_from_string(text: str, encoding) -> int:
    tokens = encoding.encode(text, disallowed_special=())
    return len(tokens)

# 토큰 수, 파일 크기 계산
def process_pdf(file_path: str, encoding) -> Tuple[str, int, int]:
    token_counts = []
    file_name = os.path.basename(file_path)
    with fitz.open(file_path) as pdf:
        for page_num in range(pdf.page_count):
            page = pdf[page_num]
            page_text = page.get_text()
            token_count = num_tokens_from_string(page_text, encoding)
            token_counts.append(token_count)
    total_tokens = sum(token_counts)
    file_size = os.path.getsize(file_path)
    print(f"{file_name} : {total_tokens} tokens, {file_size / (1024 ** 2):.2f} MB")
    return file_name, total_tokens, file_size

# 메인 실행
if __name__ == "__main__":
    # 개인 설정
    folder_path = "/Users/skan/Desktop/AI_Prototyping_Team/MS_Azure_RAG/Preprocessed_PDF"
    result_folder = "/Users/skan/Desktop/AI_Prototyping_Team/MS_Azure_RAG/Result"
    result_name = "File_Search_Cost.txt"
    model_name = "cl100k_base"
    USD = 1431.35

    # 폴더 생성
    os.makedirs(result_folder, exist_ok=True)
    result_file = os.path.join(result_folder, result_name)

    # tiktoken 설정
    encoding = tiktoken.get_encoding(model_name)

    # 파일 리스트 수집
    file_paths = [
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if f.lower().endswith(".pdf") and os.path.isfile(os.path.join(folder_path, f))
    ]

    # 병렬 계산
    all_token_counts = {}
    total_size_bytes = 0
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_file = {executor.submit(process_pdf, file_path, encoding): file_path for file_path in file_paths}
        for future in as_completed(future_to_file):
            file_name, total_tokens, file_size = future.result()
            all_token_counts[file_name] = total_tokens
            total_size_bytes += file_size

    # 크기 변환
    total_size_gb = total_size_bytes / (1024 ** 3)

    # 비용 계산
    total_tokens = sum(all_token_counts.values())
    token_cost = total_tokens * (0.13 / 1000000) * USD
    if total_size_gb <= 1:
        storage_cost = 0
    else:
        extra_gb = total_size_gb - 1
        storage_cost = extra_gb * 0.1 * USD
    cost = token_cost + storage_cost

    # 결과 저장
    lines = [f"'{file_name}' : {token_count} tokens" for file_name, token_count in all_token_counts.items()]
    lines.append("\n########################### Calculate Complete ##############################")
    lines.append(f"Total File Size: {total_size_gb:.2f} GB")
    lines.append(f"Expected Token Cost: {token_cost:.2f} KRW")
    lines.append(f"Expected Storage Cost: {storage_cost:.2f} KRW")
    lines.append(f"Expected Total Cost: {cost:.2f} KRW")
    lines.append("#############################################################################\n")
    with open(result_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"## Cost Calculation Complete ##")

