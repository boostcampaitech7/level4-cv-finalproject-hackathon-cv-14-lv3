import argparse
import os


def get_db_args():
    parser = argparse.ArgumentParser(description="Database connection configuration")
    parser.add_argument("password", help="PostgreSQL password")
    parser.add_argument("--dbname", type=str, default=os.getenv("DB_NAME", "database"))
    parser.add_argument("--user", type=str, default=os.getenv("DB_USER", "gorani"))
    parser.add_argument("--host", type=str, default=os.getenv("DB_HOST", "localhost"))
    parser.add_argument("--port", type=str, default=os.getenv("DB_PORT", "5432"))

    return parser.parse_args()
