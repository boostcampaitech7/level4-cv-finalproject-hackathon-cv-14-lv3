import asyncio
import os
import subprocess
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Configure imports and environment
EMBEDDINGS_DIR = Path(__file__).parent.parent / "database"
sys.path.append(str(EMBEDDINGS_DIR))

# Load environment variables from the embeddings directory
ROOT_DIR = Path(__file__).parents[1]
load_dotenv(ROOT_DIR / ".env")

# Initialize FastAPI app
app = FastAPI(
    title="Product Category Classification", description="Batch processing API for product category classification", version="1.0.0"
)

# Initialize category searcher
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")

# n8n webhook URL from environment variable
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")


# Pydantic models
class ProductInput(BaseModel):
    input_text: str


class BatchProductInput(BaseModel):
    products: list[ProductInput]


class ItemListInput(BaseModel):
    item_list: str


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


async def run_process(command: list[str]):
    """webshop agent 프로세스 실행"""
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)  # S603

    # Process 종료 대기
    stdout, stderr = await asyncio.to_thread(process.communicate)

    # 반환 값 처리
    if process.returncode == 0:
        return {"status": "success", "message": "Process completed successfully", "output": stdout.decode()}
    else:
        return {"status": "error", "message": "Process failed", "error": stderr.decode()}


@app.post("/purchase")
async def purchase_item(params: ItemListInput):
    """
    물품 리스트를 구매하고 결과를 n8n으로 전송하는 엔드포인트

    Request body:
    {
        "item_list": "Ruffles Ridged Potato Chips,Castor Oil Hair Shampoo,..."
    }
    """
    if not params.item_list:
        raise HTTPException(status_code=400, detail="item_list cannot be empty")
    try:
        command = [
            "python",
            "webshop_agent/run.py",
            "--num_trials",
            "1",
            "--num_envs",
            "1",
            "--run_name",
            "webshop_agent/http_run_logs_0",
            "--item_list",
            params.item_list,
            "--run_http",
        ]

        # 비동기적으로 프로세스 실행
        result = await run_process(command)
        return result
    except Exception as e:
        print(f"Error: {e!s}")
        return {"status": "error", "message": str(e)}


def main():
    import socket

    import uvicorn

    def is_port_in_use(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("0.0.0.0", port)) == 0  # S104

    port = 8888
    while is_port_in_use(port) and port < 8020:
        port += 1

    print(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)  # S104


if __name__ == "__main__":
    main()
