import os
import time
from datetime import datetime

import pytesseract
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.utils import ChromeType


class NaverShoppingInsightCapture:
    def __init__(self):
        self.chrome_options = Options()

        # Headless 모드 관련 옵션들
        self.chrome_options.add_argument("--headless=new")
        self.chrome_options.add_argument("--disable-gpu")

        # 필수 옵션들
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--window-size=1920,1080")

        # 추가 안정성을 위한 옵션들
        self.chrome_options.add_argument("--disable-extensions")
        self.chrome_options.add_argument("--remote-debugging-port=9222")
        self.chrome_options.add_argument("--disable-infobars")

        # Chromium 바이너리 경로 설정
        self.chrome_options.binary_location = "/snap/bin/chromium"

        # User-Agent 설정
        self.chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
        )

    def setup_driver(self):
        try:
            print("Chrome 드라이버 설정 중...")
            # Chromium용 드라이버 설정
            service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
            driver = webdriver.Chrome(service=service, options=self.chrome_options)
            print("Chrome 드라이버 설정 완료")
            return driver
        except Exception as e:
            print(f"드라이버 설정 중 오류 발생: {e}")
            if hasattr(e, "msg"):
                print(f"상세 오류 메시지: {e.msg}")
            return None

    def capture_page(self):
        driver = self.setup_driver()
        if not driver:
            return

        try:
            print("페이지 접속 중...")
            url = "https://datalab.naver.com/shoppingInsight/sCategory.naver"
            driver.get(url)
            print("페이지 접속 완료")

            print("페이지 로딩 대기 중...")
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "rank_top1000_list")))
            print("페이지 로딩 완료")

            driver.execute_script("window.scrollTo(0, 300)")
            time.sleep(2)

            output_dir = "output"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            print("전체 페이지 캡처 중...")
            full_screenshot_path = f"{output_dir}/full_page_{timestamp}.png"
            driver.save_screenshot(full_screenshot_path)
            print(f"전체 페이지 캡처 완료: {full_screenshot_path}")

            print("결과 영역 찾는 중...")
            results_element = driver.find_element(By.CLASS_NAME, "rank_top1000_list")
            results_screenshot_path = f"{output_dir}/results_{timestamp}.png"
            results_element.screenshot(results_screenshot_path)
            print(f"결과 영역 캡처 완료: {results_screenshot_path}")

            try:
                print("텍스트 추출 중...")
                text = pytesseract.image_to_string(Image.open(results_screenshot_path), lang="kor+eng")

                text_path = f"{output_dir}/extracted_text_{timestamp}.txt"
                with open(text_path, "w", encoding="utf-8") as f:
                    f.write(text)
                print(f"텍스트 추출 완료: {text_path}")

                print("\n=== 추출된 텍스트 ===")
                print(text[:500] + "..." if len(text) > 500 else text)

            except Exception as e:
                print(f"텍스트 추출 중 오류 발생: {e}")

        except Exception as e:
            print(f"캡처 중 오류 발생: {e}")
            print(f"오류 상세 정보: {e!s}")

        finally:
            print("브라우저 종료 중...")
            driver.quit()
            print("브라우저 종료 완료")


def main():
    crawler = NaverShoppingInsightCapture()
    crawler.capture_page()


if __name__ == "__main__":
    main()
