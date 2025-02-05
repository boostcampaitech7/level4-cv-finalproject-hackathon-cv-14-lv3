from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parents[1]
load_dotenv(ROOT_DIR / ".env")

from main import main as crawler_main

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "naver_crawler",
    default_args=default_args,
    description="Crawl Naver Shopping Insight every Monday at midnight",
    schedule_interval="0 0 * * 1",
    start_date=datetime(2024, 2, 6),
    catchup=False,
    tags=["crawler", "naver"],
)


def crawl_task():
    try:
        crawler_main()
        return "Crawling completed successfully"
    except Exception as e:
        raise Exception(f"Crawling failed: {e!s}")


crawl_operator = PythonOperator(task_id="crawl_naver_shopping", python_callable=crawl_task, dag=dag)
