# Detail
# - 만약 leaf_url에서 download button을 눌렀을때 pdf_url로 이동이 아닐때 -> 현 leaf_url을 pdf_url에 추가
# - thread 및 network 문제로 직접 처리해야 하는 error url 파일 저장 -> 추후 중복 여부 확인 필요

from concurrent.futures import ThreadPoolExecutor
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from selenium import webdriver
import os
import json
from threading import Lock

# 전역 변수
pdf_url = set()
error_url = set()
lock = Lock()

# 드라이버 설정
def configure_chrome_options():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    prefs = {
        "download.default_directory": "",
        "download.prompt_for_download": False,
        "download.directory_upgrade": False,
        "safebrowsing.enabled": False,
    }
    chrome_options.add_experimental_option("prefs", prefs)
    return chrome_options

# PDF URL 함수
def collect_pdf_url(url):
    global pdf_url, error_url

    # 드라이버 생성
    chrome_options = configure_chrome_options()
    chrome_service = Service("/opt/homebrew/bin/chromedriver")
    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    try:
        driver.get(url)
        wait = WebDriverWait(driver, 12)
        print("Visiting :", url)
        initial_url = driver.current_url
        
        # 다운로드 버튼 확인
        try:
            pdf_button = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-bi-name="download-pdf"]'))
            )
        except TimeoutException:
            with lock:
                error_url.add(url)
                print(f"Error(1) : {url}")
            return
        
        # 다운로드 버튼 클릭
        pdf_button.click()

        # PDF URL 추가
        try:
            wait.until(lambda d: d.current_url != initial_url)
            # PDF URL로 이동되는 경우
            changed_url = driver.current_url
            if "/pdf" in changed_url:
                with lock:
                    if changed_url not in pdf_url:
                        pdf_url.add(changed_url)
                        print(f"Adding   : {changed_url}")

        except TimeoutException:
            # 다운로드로 진행되는 경우
            with lock:
                if url not in pdf_url:
                    error_url.add(url)
                    print(f"Error(2) : {url}")

    except Exception as e:
        # 네트워크 및 thread 에러
        with lock:
            if url not in pdf_url:
                error_url.add(url)
            print(f"Error(3) : {url}")

    finally:
        driver.quit()

# 스레드로 작업 분배
def process_urls(url_list, max_threads=3):
    with ThreadPoolExecutor(max_threads) as executor:
        executor.map(collect_pdf_url, url_list)

# 메인 코드
if __name__ == "__main__":

    # 개인 설정
    date = "2024-11-19"
    directory = "/Users/skan/Desktop/AI_Prototyping_Team/MS_Azure_RAG/URL"

    # 파일 불러오기 (leaf_url)
    url_file_name = f"integrated_url_leaf_{date}.json"
    url_file_path = os.path.join(directory, url_file_name)
    with open(url_file_path, "r") as f:
        leaf_urls = json.load(f)

    # 스크래핑 실행
    process_urls(leaf_urls, max_threads=3)

    # 파일 저장 (error_url)
    error_url_name = f"integrated_pdf_error_{date}.json"
    error_url_path = os.path.join(directory, error_url_name)
    with open(error_url_path, "w") as f:
        json.dump(sorted(list(error_url)), f, indent=4)

    # 파일 저장 (pdf_url)
    pdf_file_name = f"integrated_pdf_{date}.json"
    pdf_file_path = os.path.join(directory, pdf_file_name)
    with open(pdf_file_path, "w") as f:
        json.dump(sorted(list(pdf_url)), f, indent=4)

    # 결과 출력
    print(f"""
            ############################## Search Complete ####################################
            Number of PDF URL: {len(pdf_url)}
            Number of Error : {len(error_url)}
            ###################################################################################
        """)