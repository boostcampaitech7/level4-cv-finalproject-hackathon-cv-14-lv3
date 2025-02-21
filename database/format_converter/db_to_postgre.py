import sqlite3
from io import StringIO

import pandas as pd
import psycopg2
from config import get_db_args
from psycopg2 import sql
from tqdm import tqdm


def convert_to_postgres():
    print("Connecting to SQLite database...")
    sqlite_conn = sqlite3.connect("train.db")

    # Read tables from SQLite
    print("Reading tables from SQLite...")
    tables = {
        "product_info": "SELECT * FROM product_info",
        "time_series_data": "SELECT * FROM time_series_data",
        "weekly_sales": "SELECT * FROM weekly_sales",
        "monthly_sales": "SELECT * FROM monthly_sales",
        "recall_info": "SELECT * FROM recall_info",
    }

    dataframes = {}
    for table_name, query in tqdm(tables.items(), desc="Loading tables"):
        dataframes[table_name] = pd.read_sql_query(query, sqlite_conn)

    sqlite_conn.close()

    # Connect to PostgreSQL
    print("Connecting to PostgreSQL...")
    args = get_db_args()
    pg_conn = psycopg2.connect(dbname=args.dbname, user=args.user, password=args.password, host=args.host, port=args.port)
    cursor = pg_conn.cursor()

    # Drop existing tables
    print("Dropping existing tables...")
    for table in tables.keys():
        cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")

    # Create tables
    print("Creating tables...")

    # Create product_info table
    cursor.execute("""
        CREATE TABLE product_info (
            id INTEGER PRIMARY KEY,
            main TEXT,
            sub1 TEXT,
            sub2 TEXT,
            sub3 TEXT
        )
    """)

    # Create time_series_data table
    cursor.execute("""
        CREATE TABLE time_series_data (
            id INTEGER PRIMARY KEY REFERENCES product_info(id)
        )
    """)

    # Create weekly_sales table
    cursor.execute("""
        CREATE TABLE weekly_sales (
            id INTEGER PRIMARY KEY REFERENCES product_info(id)
        )
    """)

    # Create monthly_sales table
    cursor.execute("""
        CREATE TABLE monthly_sales (
            id INTEGER PRIMARY KEY REFERENCES product_info(id)
        )
    """)

    # Create recall_product table
    cursor.execute("""
        CREATE TABLE recall_info (
            id INTEGER PRIMARY KEY,
            product TEXT,
            model TEXT,
            name_of_company TEXT,
            recall_type TEXT,
            barcode TEXT,
            announcement_date TEXT
        )
    """)

    # Rename DataFrame columns to lowercase
    for df in dataframes.values():
        df.columns = df.columns.str.lower()

    # Add columns for time series data
    print("Adding columns to tables...")
    for table_name, df in dataframes.items():
        if table_name in ["time_series_data", "weekly_sales", "monthly_sales"]:
            cols = [col for col in df.columns if col != "id"]
            for col in tqdm(cols, desc=f"Adding columns to {table_name}"):
                cursor.execute(
                    sql.SQL("""
                    ALTER TABLE {}
                    ADD COLUMN {} DOUBLE PRECISION
                    """).format(sql.Identifier(table_name), sql.Identifier(col))
                )

    pg_conn.commit()

    # Insert data
    print("Inserting data into tables...")
    for table_name, df in tqdm(dataframes.items(), desc="Inserting data"):
        output = StringIO()
        df.to_csv(output, sep="\t", header=False, index=False)
        output.seek(0)
        cursor.copy_from(output, table_name, null="")

    # Create indexes
    print("Creating indexes...")
    indexes = [
        ("idx_product_id", "product_info", "id"),
        ("idx_timeseries_id", "time_series_data", "id"),
        ("idx_weekwly_id", "weekly_sales", "id"),
        ("idx_monthly_id", "monthly_sales", "id"),
        ("idx_recall_info_id", "recall_info", "id"),
    ]

    for idx_name, table, column in tqdm(indexes, desc="Creating indexes"):
        cursor.execute(
            sql.SQL("CREATE INDEX IF NOT EXISTS {} ON {} ({})").format(
                sql.Identifier(idx_name), sql.Identifier(table), sql.Identifier(column)
            )
        )

    pg_conn.commit()
    pg_conn.close()

    return "Data successfully converted to PostgreSQL"


if __name__ == "__main__":
    result = convert_to_postgres()
    print(result)
