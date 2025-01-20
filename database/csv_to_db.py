import sqlite3
import pandas as pd
import random

def csv_to_sqlite(daily_csv, daily_sales_csv):
    """
    Save daily CSV data and daily sales CSV data into an SQLite database,
    plus product_info, and create an inventory table (product_inventory).
    """
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()

        # Create product_info table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_info (
            ID TEXT PRIMARY KEY,
            product TEXT,
            category TEXT,
            subcategory TEXT,
            subsubcategory TEXT,
            brand TEXT
        )
        """)

        # Create daily_data (판매수량)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_data (
            ID TEXT,
            date DATE,
            value INTEGER,
            FOREIGN KEY (ID) REFERENCES product_info(ID)
        )
        """)

        # Create daily_sales_data (판매금액)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_sales_data (
            ID TEXT,
            date DATE,
            value INTEGER,
            FOREIGN KEY (ID) REFERENCES product_info(ID)
        )
        """)


        # 재고 관리 테이블: product_inventory
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_inventory (
            ID TEXT,
            value INTEGER,
            FOREIGN KEY (ID) REFERENCES product_info(ID)
        )
        """)

        # Helper function to process time-series data
        def process_timeseries_data(df, id_col, date_cols, table_name):
            timeseries_data = []
            for _, row in df.iterrows():
                for date_col in date_cols:
                    if pd.notna(row[date_col]):
                        # (ID, 'YYYY-MM-DD', value)
                        timeseries_data.append((row[id_col], date_col, row[date_col]))
            cursor.executemany(f"INSERT INTO {table_name} VALUES (?, ?, ?)", timeseries_data)

        ###################################################
        # (1) Load 'daily.csv' => product_info + daily_data
        ###################################################
        daily_df = pd.read_csv(daily_csv)

        # product_info 채우기
        product_cols = ["ID", "제품", "대분류", "중분류", "소분류", "브랜드"]
        product_data = daily_df[product_cols].drop_duplicates().values.tolist()
        cursor.executemany("INSERT OR IGNORE INTO product_info VALUES (?, ?, ?, ?, ?, ?)", product_data)

        # 일자 칼럼(202X-XX-XX 형태)
        date_cols = [col for col in daily_df.columns if col.startswith("202")]
        process_timeseries_data(daily_df, "ID", date_cols, "daily_data")

        ###################################################
        # (2) Load 'daily_sales.csv' => daily_sales_data
        ###################################################
        daily_sales_df = pd.read_csv(daily_sales_csv)
        date_cols_sales = [col for col in daily_sales_df.columns if col.startswith("202")]
        process_timeseries_data(daily_sales_df, "ID", date_cols_sales, "daily_sales_data")

        ###################################################
        # (3) product_inventory: 100~50000 랜덤값 삽입
        ###################################################
        cursor.execute("SELECT ID FROM product_info")
        all_ids = [row[0] for row in cursor.fetchall()]

        all_ids = sorted(all_ids, key=lambda x: int(x))

        inventory_data = []
        for pid in all_ids:
            rand_value = random.randint(100, 50000)  # 20~1000 사이 정수
            inventory_data.append((pid, rand_value))

        cursor.executemany("INSERT INTO product_inventory (ID, value) VALUES (?, ?)", inventory_data)

        # Commit changes
        conn.commit()


# CSV 파일 경로
daily_csv = "train.csv"
daily_sales_csv = "sales.csv"

# 함수 호출
csv_to_sqlite(daily_csv, daily_sales_csv)
