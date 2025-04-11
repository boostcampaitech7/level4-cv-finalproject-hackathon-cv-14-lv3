import os
import sqlite3
from datetime import datetime
from typing import Any

from dotenv import load_dotenv
from supabase import create_client
from tqdm import tqdm


class SupabaseMigrator:
    def __init__(self, db_path: str):
        self.db_path = db_path
        load_dotenv()
        self.supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

    def get_table_row_count(self, cursor: sqlite3.Cursor, table_name: str) -> int:
        cursor.execute("SELECT COUNT(*) FROM ?", (table_name,))
        return cursor.fetchone()[0]

    def get_ordered_batch(self, cursor: sqlite3.Cursor, table_name: str, batch_size: int, offset: int) -> list[tuple]:
        """배치 데이터를 안전하게 조회"""
        cursor.execute("SELECT * FROM ? ORDER BY id LIMIT ? OFFSET ?", (table_name, batch_size, offset))
        return cursor.fetchall()

    def transform_product_info(self, rows: list[tuple]) -> list[dict[str, Any]]:
        return [
            {
                "id": row[0],
                "main": row[1],
                "sub1": row[2] if row[2] else None,
                "sub2": row[3] if row[3] else None,
                "sub3": row[4] if row[4] else None,
            }
            for row in rows
        ]

    def transform_monthly_sales(self, rows: list[tuple]) -> list[dict[str, Any]]:
        transformed = []
        for row in rows:
            sales_data = {
                "id": row[0],
                "2022_01": row[1],
                "2022_02": row[2],
                "2022_03": row[3],
                "2022_04": row[4],
                "2022_05": row[5],
                "2022_06": row[6],
                "2022_07": row[7],
                "2022_08": row[8],
                "2022_09": row[9],
                "2022_10": row[10],
                "2022_11": row[11],
                "2022_12": row[12],
                "2023_01": row[13],
                "2023_02": row[14],
                "2023_03": row[15],
                "2023_04": row[16],
            }
            transformed.append({k: v if v is not None else 0 for k, v in sales_data.items()})
        return transformed

    def transform_weekly_sales(self, rows: list[tuple]) -> list[dict[str, Any]]:
        transformed = []
        for row in rows:
            sales_data = {"id": row[0]}
            for i, value in enumerate(row[1:], 1):
                if i <= 52:
                    week = f"2022_w{i:02d}"
                else:
                    week = f"2023_w{i - 52:02d}"
                sales_data[week] = value if value is not None else 0
            transformed.append(sales_data)
        return transformed

    def transform_daily_sales(self, rows: list[tuple]) -> list[dict[str, Any]]:
        transformed = []
        for row in rows:
            product_id = row[0]
            for idx, value in enumerate(row[1:], 1):
                if value is not None:
                    date = datetime.strptime(row[idx], "%Y-%m-%d").date()
                    transformed.append(
                        {"id": f"{product_id}_{date}", "product_id": product_id, "sale_date": date.isoformat(), "sale_amount": value}
                    )
        return transformed

    def upload_batch_to_supabase(self, table_name: str, batch_data: list[dict[str, Any]]) -> int:
        if not batch_data:
            return 0

        try:
            self.supabase.table(table_name).upsert(batch_data).execute()
            return len(batch_data)
        except Exception as e:
            print(f"\nError during upload to {table_name}: {e}")
            return 0

    def migrate_table(self, table_name: str, batch_size: int = 100):
        transform_functions = {
            "product_info": self.transform_product_info,
            "monthly_sales": self.transform_monthly_sales,
            "weekly_sales": self.transform_weekly_sales,
            "daily_sales": self.transform_daily_sales,
        }

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            total_rows = self.get_table_row_count(cursor, table_name)
            successful = 0
            errors = 0

            with tqdm(total=total_rows, desc=f"Uploading {table_name}") as pbar:
                for offset in range(0, total_rows, batch_size):
                    try:
                        rows = self.get_ordered_batch(cursor, table_name, batch_size, offset)
                        transform_func = transform_functions.get(table_name)
                        if not transform_func:
                            raise ValueError(f"No transform function for {table_name}")

                        batch_data = transform_func(rows)
                        uploaded = self.upload_batch_to_supabase(table_name, batch_data)

                        successful += uploaded
                        if uploaded < len(batch_data):
                            errors += 1

                        pbar.update(len(batch_data))
                        pbar.set_postfix({"success": successful, "errors": errors})

                    except Exception as e:
                        print(f"\nError at offset {offset}: {e}")
                        errors += 1
                        pbar.update(batch_size)

            return total_rows, successful, errors

    def migrate_all_tables(self, batch_size: int = 100):
        # Migration order matters due to foreign key constraints
        tables = ["product_info", "monthly_sales", "weekly_sales", "daily_sales"]
        results = {}

        for table in tables:
            print(f"\nMigrating {table}...")
            total, success, fails = self.migrate_table(table, batch_size)
            results[table] = {"total": total, "success": success, "fails": fails}

        return results


def main():
    db_path = "train.db"
    batch_size = 100

    migrator = SupabaseMigrator(db_path)
    print("\nStarting migration to Supabase...")
    results = migrator.migrate_all_tables(batch_size)

    print("\nMigration completed!")
    for table, stats in results.items():
        print(f"\n{table}:")
        print(f"Total processed: {stats['total']}")
        print(f"Successfully uploaded: {stats['success']}")
        print(f"Failed: {stats['fails']}")


if __name__ == "__main__":
    main()
