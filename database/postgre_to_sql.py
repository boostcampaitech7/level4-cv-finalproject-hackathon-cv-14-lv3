import sqlite3
import pandas as pd
from config import get_db_args
from sqlalchemy import create_engine

def export_to_sqlite():
    """PostgreSQL 데이터를 SQLite로 추출"""
    args = get_db_args()
    pg_engine = create_engine(f"postgresql://{args.user}:{args.password}@{args.host}:{args.port}/{args.dbname}")

    # SQLite 데이터베이스 생성
    sqlite_conn = sqlite3.connect("database.db")
    
    try:
        # SQLite 테이블 생성
        sqlite_cursor = sqlite_conn.cursor()
        
        print("테이블 생성 중...")
        sqlite_cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_info (
            ID TEXT PRIMARY KEY,
            Main TEXT,
            Sub1 TEXT,
            Sub2 TEXT,
            Sub3 TEXT
        )
        """)

        sqlite_cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_data (
            ID TEXT,
            date DATE,
            value INTEGER,
            FOREIGN KEY (ID) REFERENCES product_info(ID)
        )
        """)

        sqlite_cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_sales_data (
            ID TEXT,
            date DATE,
            value INTEGER,
            FOREIGN KEY (ID) REFERENCES product_info(ID)
        )
        """)

        sqlite_cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_inventory (
            ID TEXT,
            value INTEGER,
            FOREIGN KEY (ID) REFERENCES product_info(ID)
        )
        """)

        # 데이터 추출 및 저장
        print("제품 정보 추출 중...")
        df_product = pd.read_sql("SELECT * FROM product_info", pg_engine)
        df_product.to_sql("product_info", sqlite_conn, if_exists="replace", index=False)

        print("일별 판매수량 데이터 추출 중...")
        df_daily = pd.read_sql("SELECT * FROM daily_data", pg_engine)
        df_daily.columns = ['ID', 'date', 'value']  # 열 이름 명시적 지정
        df_daily.to_sql("daily_data", sqlite_conn, if_exists="replace", index=False)

        print("일별 판매금액 데이터 추출 중...")
        df_sales = pd.read_sql("SELECT * FROM daily_sales_data", pg_engine)
        df_sales.columns = ['ID', 'date', 'value']  # 열 이름 명시적 지정
        df_sales.to_sql("daily_sales_data", sqlite_conn, if_exists="replace", index=False)

        print("재고 데이터 추출 중...")
        df_inventory = pd.read_sql("SELECT * FROM product_inventory", pg_engine)
        df_inventory.columns = ['ID', 'value']  # 열 이름 명시적 지정
        df_inventory.to_sql("product_inventory", sqlite_conn, if_exists="replace", index=False)

        print("데이터가 database.db 파일로 추출되었습니다!")

    except Exception as e:
        print(f"오류가 발생했습니다: {e}")
    finally:
        sqlite_conn.close()

if __name__ == "__main__":
    export_to_sqlite()