from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import json
import time
import os

# 전역 변수
lock = Lock()

# 디렉터리 생성 함수
def create_directory(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

# 드라이버 생성 함수
def create_driver(download_directory):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": download_directory,
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True
    })
    chrome_service = Service("/opt/homebrew/bin/chromedriver")
    return webdriver.Chrome(service=chrome_service, options=chrome_options)

# 다운로드 대기 함수
def wait_for_download(download_directory, timeout=90):
    start_time = time.monotonic()
    while True:
        time.sleep(0.5)
        with lock:
            files = os.listdir(download_directory)
            downloading = any(file.endswith(".crdownload") for file in files)
            download_complete = all(file.endswith(".pdf") for file in files)

        if not downloading and download_complete:
            return True
        if time.monotonic() - start_time > timeout:
            return False

# 다운로드 함수
def download_pdf(url, download_directory):
    driver = create_driver(download_directory)
    download_started = False

    try:
        driver.get(url)

        # 첫 번째 페이지 유형
        try:
            first_button = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'cr-icon-button#download[iron-icon="cr:file-download"]'))
            )
            first_button.click()
            download_started = True
        except Exception:
            pass

        # 두 번째 페이지 유형
        if not download_started:
            try:
                second_button = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-bi-name="download-pdf"]'))
                )
                second_button.click()
                download_started = True
            except Exception:
                pass

        # 다운로드 대기
        if download_started:
            if not wait_for_download(download_directory, timeout=90):
                print(f"Timeout waiting for download: {url}")
    except Exception as e:
        print(f"Error processing {url}: {e}")
    finally:
        driver.quit()

# 다운로드 실행 함수
def parallel_download(urls, download_directory, max_workers=5):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(lambda url: download_pdf(url, download_directory), urls)

# 메인 코드
if __name__ == "__main__":
    # 개인 설정
    date = "2024-11-19"
    load_directory = f"/Users/skan/Desktop/AI_Prototyping_Team/MS_Azure_RAG/URL"
    download_directory = f"/Users/skan/Desktop/AI_Prototyping_Team/MS_Azure_RAG/PDF"

    # 폴더 생성하기
    create_directory(download_directory)

    # 파일 불러오기 (pdf)
    pdf_file_name = f"integrated_pdf_{date}.json"
    pdf_file_path = os.path.join(load_directory, pdf_file_name)
    with open(pdf_file_path, "r") as f:
        pdf_urls = json.load(f)

    # 파일 불러오기 (error)
    error_file_name = f"integrated_pdf_error_{date}.json"
    error_file_path = os.path.join(load_directory, error_file_name)
    with open(error_file_path, "r") as f:
        pdf_urls_error = json.load(f)
    
    # 다운로드 실행
    parallel_download(pdf_urls, download_directory, max_workers=3)
    parallel_download(pdf_urls_error, download_directory, max_workers=3)

    # 결과 출력
    print(f"#################### Download Complete #######################")
