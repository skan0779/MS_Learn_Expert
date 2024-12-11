import os
import fitz  # PyMuPDF
import tiktoken
import time
import concurrent.futures

data_path = "/Users/skan/Desktop/AI_Prototyping_Team/MS_Azure_RAG/Failed"
new_folder = "/Users/skan/Desktop/AI_Prototyping_Team/MS_Azure_RAG/Failed2"
max_file_size_mb = 500
max_tokens = 5000000
model = "cl100k_base"
max_page_tokens = 5000000
tokenize_timeout = 15

if not os.path.exists(new_folder):
    os.makedirs(new_folder)

# 토큰 계산
def count_tokens(text):
    encoding = tiktoken.get_encoding(model)
    return len(encoding.encode(text))

# 타임아웃을 적용한 토큰화 함수
def tokenize_with_timeout(text, timeout=5):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(count_tokens, text)
        try:
            result = future.result(timeout=timeout)
            return result
        except concurrent.futures.TimeoutError:
            print("Timeout reached during tokenization.")
            return None

# PDF 파일을 분할하는 함수
def process_file(file_path):
    try:
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        print(f"Processing: {base_name}.pdf")

        with fitz.open(file_path) as pdf:
            num_pages = len(pdf)
            part = 1
            current_tokens = 0
            current_size_mb = 0
            writer = fitz.open()

            for page_num in range(num_pages):
                try:
                    page = pdf.load_page(page_num)
                    page_text = page.get_text()

                    # 타임아웃을 적용한 토큰 계산
                    page_tokens = tokenize_with_timeout(page_text, timeout=tokenize_timeout)
                    if page_tokens is None:
                        print(f"Page {page_num} skipped due to tokenization timeout.")
                        continue

                    page_size_mb = len(page_text.encode("utf-8")) / (1024 * 1024)

                    # 페이지 토큰 수가 허용 범위 초과 시 건너뛰기
                    if page_tokens > max_page_tokens:
                        print(f"Page {page_num} skipped due to token count exceeding {max_page_tokens}.")
                        continue
                    
                    # 페이지 처리
                    current_tokens += page_tokens
                    current_size_mb += page_size_mb
                    writer.insert_pdf(pdf, from_page=page_num, to_page=page_num)
                    print(f"{current_tokens} tokens, {current_size_mb:.2f} MB - {base_name}_part{part}.pdf , page {page_num}")

                    # 분할 조건 체크
                    if current_tokens > max_tokens or current_size_mb > max_file_size_mb:
                        # 이전 페이지까지 묶어서 파트로 저장
                        split_file_name = os.path.join(new_folder, f"{base_name}_part{part}.pdf")
                        writer.save(split_file_name)
                        print(f"Split: {split_file_name} - Pages: up to {page_num}")

                        # 초기화
                        part += 1
                        current_tokens = page_tokens
                        current_size_mb = page_size_mb
                        writer = fitz.open()
                        writer.insert_pdf(pdf, from_page=page_num, to_page=page_num)

                except Exception as e:
                    print(f"Error processing page {page_num} in {file_path}: {e}")
                    continue

            # 남아있는 페이지 저장
            if writer.page_count > 0:
                final_file_name = os.path.join(new_folder, f"{base_name}_part{part}.pdf")
                writer.save(final_file_name)
                print(f"Saved: {final_file_name}")

    except Exception as e:
        print(f"Error processing {file_path}: {e}")

file_paths = [os.path.join(data_path, file_name) for file_name in os.listdir(data_path) if file_name.lower().endswith('.pdf')]

# 병렬 처리 비활성
for file_path in file_paths:
    process_file(file_path)

