import sqlite3

import numpy as np
import pandas as pd


def convert_to_sqlite():
    # Read CSV and add ID
    df = pd.read_csv("train.csv")
    df.insert(0, "ID", range(1, len(df) + 1))

    # Split data
    product_info = df[["ID", "Main", "Sub1", "Sub2", "Sub3"]]
    time_series_columns = [col for col in df.columns if col.startswith("202")]
    time_series_data = df[["ID"] + time_series_columns]

    # Convert negative values to positive using absolute value
    time_series_data[time_series_columns] = np.abs(time_series_data[time_series_columns])

    # Create SQLite database
    conn = sqlite3.connect("sales_data.db")

    # Save tables with indexes
    product_info.to_sql("product_info", conn, index=False, if_exists="replace")
    time_series_data.to_sql("time_series_data", conn, index=False, if_exists="replace")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_product_id ON product_info(ID)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_timeseries_id ON time_series_data(ID)")

    conn.close()
    return "Database created with absolute values for time series data"


result = convert_to_sqlite()
print(result)
