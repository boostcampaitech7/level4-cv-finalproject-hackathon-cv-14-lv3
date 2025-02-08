import os
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator
from dotenv import load_dotenv
from naver_shopping_crawler import main as crawler_main
from product_categorizer import CategorySearch
from supabase import create_client

with DAG(
    "product_pipeline",
    default_args={
        "owner": "airflow",
        "depends_on_past": False,
        "email_on_failure": True,
        "email_on_retry": False,
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
    },
    description="Naver Shopping Trend Product Pipeline",
    schedule="0 0 * * 1",  # 매주 월요일 자정
    start_date=datetime(2024, 2, 6),
    catchup=False,
    tags=["crawler", "naver", "categorizer"],
) as dag:

    def crawl_task(**context):
        """네이버 쇼핑 크롤링 태스크"""
        try:
            # 크롤링 수행 및 결과 받기
            products = crawler_main()

            # XCom을 통해 결과 전달
            context["task_instance"].xcom_push(key="crawled_products", value=products)
            return "Crawling completed successfully"
        except Exception as e:
            raise Exception(f"Crawling failed: {e!s}")

    def categorize_task(**context):
        """상품 카테고리 분류 태스크"""
        try:
            # XCom에서 크롤링된 제품 데이터 가져오기
            task_instance = context["task_instance"]
            products = task_instance.xcom_pull(task_ids="crawl_naver_shopping", key="crawled_products")

            # Supabase 클라이언트 초기화
            root_dir = Path(__file__).parents[2]
            load_dotenv(root_dir / ".env")
            supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

            # 크롤링된 제품들 Supabase에 저장
            if products:
                supabase.table("trend_product").insert(products).execute()

            categorizer = CategorySearch()
            categorizer.load_data()

            # 제품들에 대해 카테고리 분류 수행
            order_products = []
            for product in products:
                result = categorizer.find_category(product["product_name"])

                # 모든 카테고리 레벨이 존재하는 경우에만 저장
                if result.main and result.sub1 and result.sub2 and result.sub3 and result.success and result.confidence > 0.8:
                    order_product = {
                        "main": result.main,
                        "sub1": result.sub1,
                        "sub2": result.sub2,
                        "sub3": result.sub3,
                        "quantity": 10,  # quantity 값을 10으로 설정
                    }
                    order_products.append(order_product)

            # order_product 테이블에 저장
            if order_products:
                supabase.table("order_product").insert(order_products).execute()

            return "Categorization completed successfully"
        except Exception as e:
            raise Exception(f"Categorization failed: {e!s}")

    crawl_operator = PythonOperator(task_id="crawl_naver_shopping", python_callable=crawl_task, provide_context=True, dag=dag)

    categorize_operator = PythonOperator(task_id="categorize_products", python_callable=categorize_task, provide_context=True, dag=dag)

    # 작업 순서 정의
    crawl_operator >> categorize_operator
