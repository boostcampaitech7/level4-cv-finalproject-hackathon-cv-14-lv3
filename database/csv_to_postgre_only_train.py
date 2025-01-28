import pandas as pd
import psycopg2
from config import get_db_args
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from tqdm import tqdm
import random
from psycopg2.extras import execute_values
import argparse

def get_db_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dbname", default="sales_data", help="Database name")
    parser.add_argument("--user", default="gorani", help="Database username")
    parser.add_argument("--host", default="localhost", help="Database host")
    parser.add_argument("--port", default=5432, type=int, help="Database port")
    parser.add_argument("password", help="Database password")  
    return parser.parse_args()  

def csv_to_postgresql(daily_csv: str, args) -> None:
    print("CSV 파일 읽는 중...")
    daily_df = pd.read_csv(daily_csv)

    conn = psycopg2.connect(dbname=args.dbname, user=args.user, password=args.password, host=args.host, port=args.port)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

    try:
        with conn.cursor() as cursor:
            print("📌 테이블 생성 중...")
            # 기존 테이블 삭제
            cursor.execute("DROP TABLE IF EXISTS daily_data")
            cursor.execute("DROP TABLE IF EXISTS product_inventory")
            cursor.execute("DROP TABLE IF EXISTS product_info")
            cursor.execute("DROP TABLE IF EXISTS order_table")

            # 제품 정보 테이블 (Product Info)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS product_info (
                ID VARCHAR(50) PRIMARY KEY,
                Main VARCHAR(200),
                Sub1 VARCHAR(100),
                Sub2 VARCHAR(100),
                Sub3 VARCHAR(100)
            )
            """)

            # 일별 판매량 테이블 (Daily Sales Quantity)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_data (
                ID VARCHAR(50),
                date DATE,
                value INTEGER,
                FOREIGN KEY (ID) REFERENCES product_info(ID)
            )
            """)

            # 재고 테이블 (Product Inventory)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS product_inventory (
                ID VARCHAR(50),
                value INTEGER,
                FOREIGN KEY (ID) REFERENCES product_info(ID)
            )
            """)

            # 주문 테이블 (Order Table)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_table (
                ID VARCHAR(50),
                order_quantity INTEGER,
                order_date DATE,
                PRIMARY KEY (ID, order_date)
            )
            """)

            print("✅ 제품 정보 저장 중...")
            # 제품 정보 데이터 삽입
            product_data = daily_df[["ID", "Main", "Sub1", "Sub2", "Sub3"]].drop_duplicates().values.tolist()
            cursor.executemany(
                "INSERT INTO product_info VALUES (%s, %s, %s, %s, %s)", 
                product_data
            )

            print("✅ 일별 판매수량 데이터 저장 중...")
            date_cols = [col for col in daily_df.columns if col.startswith("202")]
            daily_data = []

            print("🔄 데이터 변환 중...")
            for _, row in tqdm(daily_df.iterrows(), total=len(daily_df)):
                for date in date_cols:
                    if pd.notna(row[date]):
                        daily_data.append((row["ID"], date, int(row[date])))

            print("✅ 데이터 저장 중...")
            chunk_size = 10000
            for i in tqdm(range(0, len(daily_data), chunk_size)):
                chunk = daily_data[i:i + chunk_size]
                execute_values(
                    cursor,
                    "INSERT INTO daily_data (ID, date, value) VALUES %s",
                    chunk,
                    template="(%s, %s, %s)"
                )

            print("✅ 재고 데이터 생성 및 저장 중...")
            cursor.execute("SELECT ID FROM product_info ORDER BY ID")
            all_ids = [row[0] for row in cursor.fetchall()]
            
            inventory_data = [(pid, random.randint(10, 50000)) for pid in all_ids]
            cursor.executemany(
                "INSERT INTO product_inventory (ID, value) VALUES (%s, %s)",
                inventory_data
            )

            print("🎉 데이터베이스 변환이 완료되었습니다!")

    except Exception as e:
        print(f"오류 발생: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    args = get_db_args()
    csv_to_postgresql("train.csv", args)
