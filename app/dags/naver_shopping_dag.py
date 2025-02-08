import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parents[2]))
from naver_shopping_crawler import main as crawler_main

root_dir = Path(__file__).parents[2]
load_dotenv(root_dir / ".env")

with DAG(
    "naver_crawler",
    default_args={
        "owner": "airflow",
        "depends_on_past": False,
        "email_on_failure": True,
        "email_on_retry": False,
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
    },
    description="Crawl Naver Shopping Insight every Monday at midnight",
    schedule="0 0 * * 1",
    start_date=datetime(2024, 2, 6),
    catchup=False,
    tags=["crawler", "naver"],
) as dag:

    def crawl_task():
        try:
            crawler_main()
            return "Crawling completed successfully"
        except Exception as e:
            raise Exception(f"Crawling failed: {e!s}") from e

    crawl_operator = PythonOperator(task_id="crawl_naver_shopping", python_callable=crawl_task, dag=dag)
