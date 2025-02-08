from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator
from dotenv import load_dotenv
from product_categorizer import CategorySearch  # 같은 디렉토리의 product_categorizer.py에서 import

root_dir = Path(__file__).parents[2]
load_dotenv(root_dir / ".env")

with DAG(
    "product_categorizer",
    default_args={
        "owner": "airflow",
        "depends_on_past": False,
        "email_on_failure": True,
        "email_on_retry": False,
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
    },
    description="Categorize products from Naver Shopping Insight",
    schedule="30 0 * * 1",  # 크롤링 작업 30분 후 실행
    start_date=datetime(2024, 2, 6),
    catchup=False,
    tags=["categorizer", "naver"],
) as dag:

    def categorize_task():
        try:
            categorizer = CategorySearch()
            categorizer.load_data()

            for product in categorizer.trend_products:
                result = categorizer.find_category(product["product_name"])
                categorizer.save_category_result(result)

            return "Categorization completed successfully"
        except Exception as e:
            raise Exception(f"Categorization failed: {e!s}")

    categorize_operator = PythonOperator(task_id="categorize_products", python_callable=categorize_task, dag=dag)
