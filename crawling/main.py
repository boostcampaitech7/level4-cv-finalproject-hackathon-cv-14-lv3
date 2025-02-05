import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


def capture_screenshot(url, output_file="screenshot.png"):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # 아래 옵션들을 추가
    options.add_argument("--remote-debugging-port=9222")  # 디버깅 포트 지정
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1280,1024")

    # Chrome binary 위치를 명시적으로 지정 (필요한 경우)
    # options.binary_location = "/usr/bin/google-chrome"

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(url)
        # 페이지 로딩을 위한 대기 시간을 조금 더 늘림
        time.sleep(5)
        driver.save_screenshot(output_file)
        print(f"Screenshot saved: {output_file}")
    finally:
        driver.quit()


if __name__ == "__main__":
    capture_screenshot("https://datalab.naver.com/shoppingInsight/sCategory.naver?cid=50000003")
