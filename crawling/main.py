import os
import time
from pathlib import Path

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tqdm import tqdm
from webdriver_manager.chrome import ChromeDriverManager


def capture_screenshot(driver, url, output_file):
    try:
        driver.get(url)
        wait = WebDriverWait(driver, 10)

        # 1. 먼저 컨테이너 찾기
        element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.section_instie_area.space_right")))

        # 2. 전체 목록이 로드되도록 스크롤 처리
        # 컨테이너 상단으로 스크롤
        driver.execute_script("arguments[0].scrollIntoView(true);", element)
        time.sleep(1)

        # 컨테이너 내부에서 추가 스크롤
        driver.execute_script(
            """
            let element = arguments[0];
            let scrollHeight = element.scrollHeight;
            for(let i = 0; i < scrollHeight; i += 100) {
                element.scrollTo(0, i);
            }
            element.scrollTo(0, 0);  // 다시 맨 위로
        """,
            element,
        )
        time.sleep(2)  # 스크롤 후 대기

        # 3. 요소의 실제 크기 계산
        actual_height = driver.execute_script(
            """
            let element = arguments[0];
            let items = element.querySelectorAll('.rank_item');  // 순위 아이템들
            if (items.length > 0) {
                let lastItem = items[items.length - 1];
                return lastItem.offsetTop + lastItem.offsetHeight - element.offsetTop;
            }
            return element.scrollHeight;
        """,
            element,
        )

        # 4. 위치와 크기 정보 가져오기
        location = element.location
        size = element.size
        size["height"] = max(size["height"], actual_height)  # 실제 높이 적용

        print(f"Element location: {location}")
        print(f"Element size: {size}")
        print(f"Actual height: {actual_height}")

        # 5. 전체 스크린샷
        driver.save_screenshot(str(output_file))

        # 6. 이미지 크롭
        from PIL import Image

        im = Image.open(output_file)

        # 여백 설정
        padding = 10
        left = max(0, location["x"] - padding)
        top = max(0, location["y"] - padding)
        right = min(im.width, location["x"] + size["width"] + padding)
        bottom = min(im.height, location["y"] + size["height"] + padding)

        # 이미지 자르기
        im = im.crop((left, top, right, bottom))
        im.save(output_file)

        print(f"Screenshot saved: {output_file}")
        return True

    except Exception as e:
        print(f"Error capturing screenshot: {e!s}")
        print(f"Error type: {type(e)}")
        import traceback

        print(traceback.format_exc())
        return False


def setup_chrome_options():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    # 창 크기를 더 크게 설정
    options.add_argument("--window-size=1920,2000")  # 세로 크기 증가
    return options


def main():
    # .env 파일 로드
    load_dotenv()
    base_url = os.getenv("BASE_URL")

    # 임시 디렉토리 정리
    import shutil

    chrome_data_dir = "/tmp/chrome-data"
    if os.path.exists(chrome_data_dir):
        shutil.rmtree(chrome_data_dir)

    # 출력 디렉토리 생성
    output_dir = Path("screenshots")
    output_dir.mkdir(exist_ok=True)

    # Chrome 드라이버 설정
    service = Service(ChromeDriverManager().install())
    options = setup_chrome_options()

    failed_urls = []

    try:
        driver = webdriver.Chrome(service=service, options=options)

        # URL 순회하며 스크린샷 캡처
        for i in tqdm(range(2), desc="Capturing screenshots"):
            url = f"{base_url}{i:02d}"
            output_file = output_dir / f"screenshot_{i:02d}.png"

            if not capture_screenshot(driver, url, output_file):
                failed_urls.append(url)

            time.sleep(2)  # 요청 간 간격

    except Exception as e:
        print(f"Main process error: {e!s}")

    finally:
        try:
            driver.quit()
        except:
            pass

        # 임시 디렉토리 정리
        if os.path.exists(chrome_data_dir):
            shutil.rmtree(chrome_data_dir)

    # 실패한 URL 보고
    if failed_urls:
        print("\nFailed URLs:")
        for url in failed_urls:
            print(url)


if __name__ == "__main__":
    main()
