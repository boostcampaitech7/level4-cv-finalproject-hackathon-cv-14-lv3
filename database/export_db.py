import sqlite3

import pandas as pd
from config import get_db_args
from sqlalchemy import create_engine

""" PostgreSQL 데이터를 SQLite로 추출합니다. """


def export_to_sqlite():
    """PostgreSQL 데이터를 SQLite로 추출"""
    # PostgreSQL 연결 설정
    args = get_db_args()
    pg_engine = create_engine(f"postgresql://{args.user}:{args.password}@{args.host}:{args.port}/{args.dbname}")

    # SQLite 데이터베이스 생성
    sqlite_conn = sqlite3.connect("sales_data.db")

    try:
        # product_info 테이블 추출 및 저장
        print("제품 정보 추출 중...")
        df_product = pd.read_sql("SELECT * FROM product_info", pg_engine)
        df_product.to_sql("product_info", sqlite_conn, if_exists="replace", index=False)

        # time_series_data 테이블 추출 및 저장
        print("시계열 데이터 추출 중...")
        df_timeseries = pd.read_sql("SELECT * FROM time_series_data", pg_engine)
        df_timeseries.to_sql("time_series_data", sqlite_conn, if_exists="replace", index=False)

        print("데이터가 sales_data.db 파일로 추출되었습니다!")

    except Exception as e:
        print(f"오류가 발생했습니다: {e}")
    finally:
        sqlite_conn.close()


if __name__ == "__main__":
    export_to_sqlite()
