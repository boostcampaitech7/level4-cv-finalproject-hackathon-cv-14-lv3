import os
import sys
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

    Request body example:
    {
    "results": [
        {
        "input_text": "Cheese burger",
        "categories": {
            "main": "Grocery & Gourmet Food",
            "sub1": "Fresh Produce",
            "sub2": "Baking",
            "sub3": "Bread Baking"
        }}]}
    """
    try:
        results = []

        for product in batch.products:
            # 카테고리 분류 실행
            categories = searcher.find_best_category(product.input_text)

            # 필요한 데이터만 포함
            result = {"input_text": product.input_text, "categories": categories}
            results.append(result)

        # Prepare data for n8n
        n8n_data = {"results": results}

        # Attempt to send to n8n webhook (non-blocking)
        await send_to_n8n(n8n_data)

        # Return response
        return {"status": "success", "results": results}

    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err)) from err


def main():
    import socket

    import uvicorn

    def is_port_in_use(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("0.0.0.0", port)) == 0  # S104

    port = 8000
    while is_port_in_use(port) and port < 8020:
        port += 1

    print(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)  # S104


if __name__ == "__main__":
    main()
