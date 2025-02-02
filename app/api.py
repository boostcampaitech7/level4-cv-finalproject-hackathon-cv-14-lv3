import os
import sys
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Configure imports and environment
EMBEDDINGS_DIR = Path(__file__).parent.parent / "database"
sys.path.append(str(EMBEDDINGS_DIR))

from category_search import HierarchicalCategorySearch  # noqa: E402

# Load environment variables from the embeddings directory
ENV_PATH = EMBEDDINGS_DIR / ".env"
load_dotenv(ENV_PATH)

# Initialize FastAPI app
app = FastAPI(
    title="Product Category Classification", description="Batch processing API for product category classification", version="1.0.0"
)

# Initialize category searcher
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
searcher = HierarchicalCategorySearch(url, key)

# n8n webhook URL from environment variable
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")


# Pydantic models
class ProductInput(BaseModel):
    input_text: str


class BatchProductInput(BaseModel):
    products: list[ProductInput]


async def send_to_n8n(data: dict):
    """Send results to n8n webhook"""
    if not N8N_WEBHOOK_URL:
        print("Warning: N8N_WEBHOOK_URL is not configured, skipping webhook")
        return

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(N8N_WEBHOOK_URL, json=data)
            if response.status_code != 200:
                print(f"Warning: Failed to send data to n8n. Status: {response.status_code}")
    except Exception as e:
        print(f"Warning: Error sending data to n8n: {e!s}")


@app.post("/process-batch")
async def process_batch(batch: BatchProductInput):
    """
    배치 단위로 상품을 처리하고 결과를 n8n으로 전송하는 엔드포인트

    Request body:
    {
        "products": [
            {"input_text": "gaming laptop"},
            {"input_text": "organic banana"},
            ...
        ]
    }
    """
    try:
        results = []
        processed_time = datetime.now().isoformat()

        for product in batch.products:
            # 카테고리 분류 실행
            categories = searcher.find_best_category(product.input_text)

            # 결과 데이터 구성
            result = {"input_text": product.input_text, "categories": categories, "processed_at": processed_time}
            results.append(result)

        # Prepare data for n8n
        n8n_data = {"batch_id": processed_time, "processed_count": len(results), "results": results}

        # Attempt to send to n8n webhook (non-blocking)
        await send_to_n8n(n8n_data)

        # Return response
        return {"status": "success", "processed_count": len(results), "processed_at": processed_time, "results": results}

    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err)) from err


def main():
    import time

    import psutil
    import uvicorn

    def kill_process_on_port(port):
        """주어진 포트를 사용하는 프로세스를 찾아서 종료"""
        for proc in psutil.process_iter(["pid", "name", "connections"]):
            try:
                for conn in proc.connections():
                    if conn.laddr.port == port:
                        psutil.Process(proc.pid).terminate()
                        time.sleep(1)
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False

    # 8000번 포트 사용 중인 프로세스 종료
    if kill_process_on_port(8000):
        print("Killed existing process on port 8000")

    # FastAPI 서버 시작 (localhost만 허용)
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
