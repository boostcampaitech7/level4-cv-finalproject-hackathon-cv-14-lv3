import sqlite3
import pandas as pd

def csv_to_sqlite(daily_csv, weekly_csv, monthly_csv, daily_sales_csv, weekly_sales_csv, monthly_sales_csv):
    """
    Save daily, weekly, and monthly CSV data into an SQLite database.
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

        # Create time-series data tables
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_data (
            ID TEXT,
            date DATE,
            value INTEGER,
            FOREIGN KEY (ID) REFERENCES product_info(ID)
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS weekly_data (
            ID TEXT,
            week_start_date DATE,
            value INTEGER,
            FOREIGN KEY (ID) REFERENCES product_info(ID)
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS monthly_data (
            ID TEXT,
            month_start_date DATE,
            value INTEGER,
            FOREIGN KEY (ID) REFERENCES product_info(ID)
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_sales_data (
            ID TEXT,
            date DATE,
            value INTEGER,
            FOREIGN KEY (ID) REFERENCES product_info(ID)
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS weekly_sales_data (
            ID TEXT,
            week_start_date DATE,
            value INTEGER,
            FOREIGN KEY (ID) REFERENCES product_info(ID)
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS monthly_sales_data (
            ID TEXT,
            month_start_date DATE,
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
                        timeseries_data.append((row[id_col], date_col, row[date_col]))
            cursor.executemany(f"INSERT INTO {table_name} VALUES (?, ?, ?)", timeseries_data)

        # Process daily data
        daily_df = pd.read_csv(daily_csv)
        product_cols = ["ID", "제품", "대분류", "중분류", "소분류", "브랜드"]
        product_data = daily_df[product_cols].drop_duplicates().values.tolist()
        cursor.executemany("INSERT OR IGNORE INTO product_info VALUES (?, ?, ?, ?, ?, ?)", product_data)
        date_cols = [col for col in daily_df.columns if col.startswith("202")]
        process_timeseries_data(daily_df, "ID", date_cols, "daily_data")

        # Process weekly data
        weekly_df = pd.read_csv(weekly_csv)
        date_cols = [col for col in weekly_df.columns if "202" in col]
        process_timeseries_data(weekly_df, "ID", date_cols, "weekly_data")

        # Process monthly data
        monthly_df = pd.read_csv(monthly_csv)
        date_cols = [col for col in monthly_df.columns if "202" in col]
        process_timeseries_data(monthly_df, "ID", date_cols, "monthly_data")

        # Process daily sales data
        daily_sales_df = pd.read_csv(daily_sales_csv)
        date_cols = [col for col in daily_sales_df.columns if col.startswith("202")]
        process_timeseries_data(daily_sales_df, "ID", date_cols, "daily_sales_data")

        # Process weekly sales data
        weekly_sales_df = pd.read_csv(weekly_sales_csv)
        date_cols = [col for col in weekly_sales_df.columns if "202" in col]
        process_timeseries_data(weekly_sales_df, "ID", date_cols, "weekly_sales_data")

        # Process monthly sales data
        monthly_sales_df = pd.read_csv(monthly_sales_csv)
        date_cols = [col for col in monthly_sales_df.columns if "202" in col]
        process_timeseries_data(monthly_sales_df, "ID", date_cols, "monthly_sales_data")

        # Commit changes
        conn.commit()


# 판매량 데이터 파일 경로 지정
daily_csv = "daily_sales_volume.csv"
weekly_csv = "weekly_sales_volume.csv"
monthly_csv = "monthly_sales_volume.csv"
# 판매금액 데이터 파일 경로 지정
daily_sales_csv = "daily_sales.csv"
weekly_sales_csv = "weekly_sales.csv"
monthly_sales_csv = "monthly_sales.csv"

# Call the function with provided files
csv_to_sqlite(daily_csv, weekly_csv, monthly_csv,
              daily_sales_csv, weekly_sales_csv, monthly_sales_csv)


