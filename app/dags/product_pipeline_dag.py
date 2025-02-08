import os
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator
from dotenv import load_dotenv
from naver_shopping_crawler import main as crawler_main
from product_categorizer import CategorySearch
from supabase import create_client

ROOT_DIR = Path(__file__).parents[2]  # Project rot directory

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
            # Load .env
            load_dotenv(ROOT_DIR / ".env")

            # 크롤링 수행 및 결과 받기
            products = crawler_main()

            # start_date와 end_date 추가
            today = datetime.now().strftime("%Y-%m-%d")
            enriched_products = [{**product, "start_date": today, "end_date": today} for product in products]

            # XCom을 통해 결과 전달
            context["task_instance"].xcom_push(key="crawled_products", value=enriched_products)
            return "Crawling completed successfully"
        except Exception as e:
            raise Exception(f"Crawling failed: {e!s}")

    def categorize_task(**context):
        """상품 카테고리 분류 태스크"""
        try:
            # .env 파일 로드
            load_dotenv(ROOT_DIR / ".env")

            # Supabase 클라이언트 초기화
            supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

            # trend_product 테이블에서 데이터 로드
            response = supabase.table("trend_product").select("*, id").execute()
            products = response.data

            if not products:
                print("No products found in trend_product table")
                return "No products to categorize"

            print(f"Loaded {len(products)} products from trend_product table")

            # 카테고리 분류기 초기화 및 데이터 로드
            categorizer = CategorySearch()
            categorizer.load_data()

            # 제품들에 대해 카테고리 분류 수행
            order_products = []
            success_count = 0
            fail_count = 0

            for product in products:
                try:
                    print(f"\n{'='*50}")
                    print(f"Processing product: {product['product_name']}")

                    result = categorizer.find_category(product["product_name"])

                    # 상세 결과 출력
                    print("Category Result:")
                    print(f"- Main: {result.main}")
                    print(f"- Sub1: {result.sub1}")
                    print(f"- Sub2: {result.sub2}")
                    print(f"- Sub3: {result.sub3}")
                    print(f"- Confidence: {result.confidence}")
                    print(f"- Success: {result.success}")

                    # sub3까지 모든 카테고리가 있는 경우에만 저장
                    if result.main and result.sub1 and result.sub2 and result.sub3 and result.success and result.confidence > 0.6:
                        order_product = {
                            "id": product["id"],
                            "main": result.main,
                            "sub1": result.sub1,
                            "sub2": result.sub2,
                            "sub3": result.sub3,
                            "quantity": 10,
                        }
                        order_products.append(order_product)
                        success_count += 1
                        print(
                            f"✅ Successfully categorized: {product['product_name']} -> Complete category path: "
                            f"{result.main}/{result.sub1}/{result.sub2}/{result.sub3}"
                        )
                    else:
                        fail_count += 1
                        print(f"❌ Failed to categorize: {product['product_name']}")
                        if not result.sub3:
                            print("Failure reason: Incomplete category path (missing sub3)")
                        elif not result.success:
                            print("Failure reason: Classification not successful")
                        else:
                            print(f"Failure reason: Low confidence ({result.confidence})")

                except Exception as e:
                    fail_count += 1
                    print(f"❌ Error processing {product['product_name']}: {e!s}")

            # 결과 요약
            print("\n" + "=" * 50)
            print("Categorization Summary:")
            print(f"Total products processed: {len(products)}")
            print(f"Successfully categorized: {success_count}")
            print(f"Failed to categorize: {fail_count}")
            print(f"Success rate: {(success_count/len(products))*100:.2f}%")

            # order_product 테이블에 저장
            if order_products:
                try:
                    result = supabase.table("order_product").insert(order_products).execute()
                    print(f"\nSaved {len(order_products)} products to order_product table")
                except Exception as e:
                    print(f"\nError saving to order_product: {e}")
            else:
                print("\nNo products met the complete category path criteria for order_product table")

            return "Categorization completed successfully"

        except Exception as e:
            raise Exception(f"Categorization failed: {e!s}")

    crawl_operator = PythonOperator(task_id="crawl_naver_shopping", python_callable=crawl_task, provide_context=True, dag=dag)

    categorize_operator = PythonOperator(task_id="categorize_products", python_callable=categorize_task, provide_context=True, dag=dag)

    # 작업 순서 정의
    crawl_operator >> categorize_operator
