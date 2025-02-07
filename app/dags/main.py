import os
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from supabase import create_client
from tqdm import tqdm
from webdriver_manager.chrome import ChromeDriverManager

ROOT_DIR = Path(__file__).parents[1]
load_dotenv(ROOT_DIR / ".env")

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def setup_chrome_options():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1024,1080")
    return options


def capture_screenshot(driver, url, output_file):
    try:
        driver.get(url)
        time.sleep(3)
        driver.save_screenshot(str(output_file))

        with Image.open(output_file) as im:
            width, height = im.size
            cropped = im.crop((width * 5 / 6, height * 2 / 3, width, height))
            cropped.save(output_file)
        return True
    except Exception as e:
        print(f"Screenshot error: {e}")
        return False


CATEGORIES = ["패션 잡화", "화장품 미용", "디지털 가전", "가구 인테리어", "출산 육아", "식품", "스포츠 레저", "생활 건강", "여가 생활 편의"]


def extract_data(ocr_result, category_idx):
    current_date = datetime.now().strftime("%y-%m-%d")
    lines = ocr_result["pages"][0]["text"].split("\n")

    valid_products = {}
    for line in lines:
        words = line.strip().split()
        for i, word in enumerate(words[:-1]):
            if word.isdigit():
                rank = int(word)
                if 1 <= rank <= 10:
                    product = words[i + 1].strip()
                    if product == current_date or product.isdigit():
                        continue
                    if rank not in valid_products or len(product) > len(valid_products[rank]):
                        valid_products[rank] = product

    return sorted(
        [{"category": CATEGORIES[category_idx - 1], "rank": rank, "product_name": product} for rank, product in valid_products.items()],
        key=lambda x: x["rank"],
    )


def trigger_n8n_webhook():
    # n8n webhook URL
    webhook_url = "http://localhost:5678/webhook/trending"
    try:
        response = requests.post(webhook_url)
        if response.status_code == 200:
            print("N8n workflow triggered successfully")
        else:
            print(f"Failed to trigger n8n workflow: {response.status_code}")
    except Exception as e:
        print(f"Error triggering n8n workflow: {e!s}")


def save_to_supabase(rankings):
    try:
        if rankings:
            result = supabase.table("trend_product").insert(rankings).execute()
            print(f"Saved {len(rankings)} items")
            trigger_n8n_webhook()  # db 저장 후 n8n workflow trigger
            return result
    except Exception as e:
        print(f"Database error: {e}")
        return None


def ocr_image(image_path):
    api_key = os.getenv("UPSTAGE_API_KEY")
    url = os.getenv("UPSTAGE_OCR_URL")
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        with open(image_path, "rb") as image_file:
            files = {"document": image_file}
            response = requests.post(url, headers=headers, files=files)

        if response.status_code != 200:
            print(f"OCR error: {response.text}")
            return None

        return response.json()
    except Exception as e:
        print(f"OCR processing error: {e}")
        return None


def main():
    screenshots_dir = Path(__file__).parent / "src"

    if screenshots_dir.exists():
        for file in screenshots_dir.glob("*"):
            file.unlink()
    else:
        screenshots_dir.mkdir()

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=setup_chrome_options())
    failed_urls = []

    try:
        base_url = os.getenv("BASE_URL")
        for i in tqdm(range(1, 10), desc="Processing"):
        url = f"{base_url}{i}"
        output_file = screenshots_dir / f"screenshot_{i:02d}.png"

        if capture_screenshot(driver, url, output_file):
            result = ocr_image(output_file)
            if result:
                rankings = extract_data(result, i)
                if rankings:
                    save_to_supabase(rankings)
        else:
            failed_urls.append(url)
        time.sleep(1)

    except Exception as e:
        print(f"Main error: {e}")
    finally:
        driver.quit()

    if failed_urls:
        print("\nFailed URLs:", *failed_urls, sep="\n")


if __name__ == "__main__":
    main()
