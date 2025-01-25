import sqlite3

import pandas as pd
import psycopg2
from config import get_db_args
from psycopg2 import sql


def convert_to_postgres():
    args = get_db_args()

    sqlite_conn = sqlite3.connect("sales_data.db")
    product_info = pd.read_sql_query("SELECT * FROM product_info", sqlite_conn)
    time_series = pd.read_sql_query("SELECT * FROM time_series_data", sqlite_conn)
    sqlite_conn.close()

    pg_conn = psycopg2.connect(dbname=args.dbname, user=args.user, password=args.password, host=args.host, port=args.port)
    cursor = pg_conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS time_series_data CASCADE")
    cursor.execute("DROP TABLE IF EXISTS product_info CASCADE")

    cursor.execute("""
        CREATE TABLE product_info (
            ID INTEGER PRIMARY KEY,
            Main TEXT,
            Sub1 TEXT,
            Sub2 TEXT,
            Sub3 TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE time_series_data (
            ID INTEGER PRIMARY KEY REFERENCES product_info(ID)
        )
    """)

    time_cols = [col for col in time_series.columns if col != "ID"]
    for col in time_cols:
        cursor.execute(
            sql.SQL("""
            ALTER TABLE time_series_data
            ADD COLUMN {} INTEGER
        """).format(sql.Identifier(col))
        )

    pg_conn.commit()

    # Use StringIO for faster data insertion
    from io import StringIO

    for table, data in [("product_info", product_info), ("time_series_data", time_series)]:
        output = StringIO()
        data.to_csv(output, sep="\t", header=False, index=False)
        output.seek(0)
        cursor.copy_from(output, table, null="")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_product_id ON product_info(ID)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_timeseries_id ON time_series_data(ID)")

    pg_conn.commit()
    pg_conn.close()

    return "Data successfully converted to PostgreSQL"


if __name__ == "__main__":
    result = convert_to_postgres()
    print(result)
