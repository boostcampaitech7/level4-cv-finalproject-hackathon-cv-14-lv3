import sqlite3

import numpy as np
import pandas as pd
from tqdm import tqdm


def convert_to_sqlite():
    # Read CSV and add ID
    df = pd.read_csv("train.csv")

    # Split data
    print("Processing product info...")
    product_info = df[["ID", "Main", "Sub1", "Sub2", "Sub3"]]
    time_series_columns = [col for col in df.columns if col.startswith("202")]
    time_series_data = df[["ID", *time_series_columns]]

    # Create empty recall information table
    print("Creating empty recall information table...")
    recall_info = pd.DataFrame(columns=["ID", "product", "model", "name_of_company", "recall_type", "barcode", "announcement_date"])

    # Convert negative values to positive using absolute value
    print("Converting negative values to absolute values...")
    time_series_data[time_series_columns] = np.abs(time_series_data[time_series_columns])

    # Create weekly and monthly aggregations
    print("Creating weekly and monthly aggregations...")
    # Melt the time series data with progress bar
    print("Melting time series data...")
    melted_data = pd.DataFrame()
    chunk_size = 1000  # Process in chunks to show progress

    for i in tqdm(range(0, len(time_series_data), chunk_size), desc="Melting data"):
        chunk = time_series_data.iloc[i : i + chunk_size].melt(
            id_vars=["ID"], value_vars=time_series_columns, var_name="date", value_name="sales"
        )
        melted_data = pd.concat([melted_data, chunk], ignore_index=True)

    # Convert date strings to datetime objects
    print("Converting dates...")
    melted_data["date"] = pd.to_datetime(melted_data["date"])

    # Create weekly aggregation with pivot
    print("Creating weekly sales table...")
    weekly_sales = melted_data.copy()
    weekly_sales["year_week"] = weekly_sales["date"].dt.strftime("%Y-%V")
    # Group by ID and year_week first
    weekly_agg = weekly_sales.groupby(["ID", "year_week"])["sales"].sum().reset_index()
    # Pivot to have weeks as columns
    weekly_sales_pivot = weekly_agg.pivot(index="ID", columns="year_week", values="sales").reset_index()
    # Fill NaN values with 0
    weekly_sales_pivot = weekly_sales_pivot.fillna(0)

    # Create monthly aggregation with pivot (similar to weekly)
    print("Creating monthly sales table...")
    monthly_sales = melted_data.copy()
    monthly_sales["year_month"] = monthly_sales["date"].dt.strftime("%Y-%m")
    # Group by ID and year_month first
    monthly_agg = monthly_sales.groupby(["ID", "year_month"])["sales"].sum().reset_index()
    # Pivot to have months as columns
    monthly_sales_pivot = monthly_agg.pivot(index="ID", columns="year_month", values="sales").reset_index()
    # Fill NaN values with 0
    monthly_sales_pivot = monthly_sales_pivot.fillna(0)

    # Create SQLite database
    print("Creating SQLite database...")
    conn = sqlite3.connect("train.db")

    # Save tables with indexes
    print("Saving tables to database...")
    for table_name, df in tqdm(
        [
            ("product_info", product_info),
            ("time_series_data", time_series_data),
            ("weekly_sales", weekly_sales_pivot),
            ("monthly_sales", monthly_sales_pivot),
            ("recall_info", recall_info),  # Added new table
        ],
        desc="Saving tables",
    ):
        df.to_sql(table_name, conn, index=False, if_exists="replace")

    # Create indexes
    print("Creating indexes...")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_product_id ON product_info(ID)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_timeseries_id ON time_series_data(ID)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_recall_id ON recall_info(ID)")  # Added new index

    conn.close()
    return "Database created with daily, weekly, and monthly sales aggregations, and empty recall information table"


if __name__ == "__main__":
    result = convert_to_sqlite()
    print(result)
