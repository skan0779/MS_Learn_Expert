# Detail
# 1. 시작 페이지에서 <div class="card-content"> 태그 모두 추출
# 2. 해당 <div> 내부 모든 <a> 의 data-linktype 속성값에 따라 href 속성값 처리 (target_url에 <a href="~"> 링크 추가)
#   - "relative-path" : "https://learn.microsoft.com" + href
#   - "absolute-path" : 현링크 url/ 까지 (?가 있을경우 제거)
#   - "external" : 제외
# 3. target_url que에 처리한 모든 <a href="~"> 링크 추가
# 3. 들어간 페이지에 <button> 중 data-bi-name="download-pdf" 태그가 있을때 leaf_urls에 추가 후 해당 페이지 종료
# 4. 아니면 페이지에 <div class="card-content"> 가 없을때 해당 페이지 종료
# 5. visited_url.json 파일로 중복 조회 공용 관리

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from collections import deque
import json
import datetime
import os
from urllib.parse import urljoin

# 개인 설정
service = "azure"
date = "2024-11-19"
directory = "/Users/skan/Desktop/AI_Prototyping_Team/MS_Azure_RAG/URL"

# 변수 설정
start_url = f"https://learn.microsoft.com/en-us/{service}/"
target_url = deque()
leaf_urls = set()

# 드라이버 설정
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_service = Service("/opt/homebrew/bin/chromedriver")
driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

# 파일 불러오기 (visited_url)
os.makedirs(directory, exist_ok=True)
visited_file_name = f"integrated_url_visited_{date}.json"
visited_file_path = os.path.join(directory, visited_file_name)
if os.path.exists(visited_file_path):
    with open(visited_file_path, "r") as f:
        visited_urls = set(json.load(f))
else:
    visited_urls = set()

# 파일 불러오기 (leaf_url)
leaf_file_name = f"integrated_url_leaf_{date}.json"
leaf_file_path = os.path.join(directory, leaf_file_name)
if os.path.exists(leaf_file_path):
    with open(leaf_file_path, "r") as f:
        integrated_leaf_urls = set(json.load(f))
else:
    integrated_leaf_urls = set()

# 링크 추가 함수
def add_links_to_queue(url):
    driver.get(url)
    try:
        wait = WebDriverWait(driver, 1.5)

        # 다운로드 버튼 확인
        try:
            download_button = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "button[data-bi-name='download-pdf']"))
            )
            leaf_urls.add(url)
            print(f"Adding   : {url}")
            return
        except TimeoutException:
            pass

        # <div class="card-content"> 확인
        try:
            card_contents = wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.card-content"))
            )
        except TimeoutException:
            return

        # <a href="~" data-linktype="~"> 확인
        for card_content in card_contents:
            links = card_content.find_elements(By.TAG_NAME, "a")

            # 모든 <a> 확인
            for link in links:
                next_url = link.get_attribute("href")
                link_type = link.get_attribute("data-linktype")

                # data-linktype에 따른 href 수정
                if link_type == "relative-path":
                    next_url = urljoin(url, next_url)
                elif link_type == "absolute-path":
                    if "https://learn.microsoft.com" in next_url:
                        pass
                    else:
                        next_url = f"https://learn.microsoft.com{next_url}"
                elif link_type == "external":
                    continue

                # Que에 추가
                if next_url and next_url not in visited_urls:
                    target_url.append(next_url)
                    visited_urls.add(next_url)

    except Exception as e:
        pass

# 링크 추가 실행
target_url.append(start_url)
visited_urls.add(start_url)

while target_url:
    current_url = target_url.popleft()
    print("Visiting :", current_url)
    try:
        add_links_to_queue(current_url)
    except Exception as e:
        print(f"Error    : {current_url}")
        pass

driver.quit()

# 파일 저장 (공용 visited_url)
current_date = datetime.datetime.now().strftime("%Y-%m-%d")
new_visited_file_name = f"integrated_url_visited_{current_date}.json"
new_visited_file_path = os.path.join(directory, new_visited_file_name)
with open(new_visited_file_path, "w") as f:
    json.dump(sorted(list(visited_urls)), f, indent=4)

# 파일 저장 (공용 leaf_url)
integrated_leaf_urls.update(leaf_urls)
new_leaf_file_name = f"integrated_url_leaf_{current_date}.json"
new_leaf_file_path = os.path.join(directory, new_leaf_file_name)
with open(new_leaf_file_path, "w") as f:
    json.dump(sorted(list(integrated_leaf_urls)), f, indent=4)

# 결과 출력
print(f"""
        ############################## Search Complete ####################################
        Number of Total Leaf URL : {len(integrated_leaf_urls)}
        Number of New Leaf URL : {len(leaf_urls)}
        ###################################################################################
    """)