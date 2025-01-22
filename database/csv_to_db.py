import pandas as pd
import psycopg2
from config import get_db_args
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from tqdm import tqdm


def csv_to_postgresql(csv_path: str, args) -> None:
    print("CSV 파일 읽는 중...")
    df = pd.read_csv(csv_path)

    conn = psycopg2.connect(dbname=args.dbname, user=args.user, password=args.password, host=args.host, port=args.port)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

    try:
        with conn.cursor() as cursor:
            print("테이블 생성 중...")
            cursor.execute("DROP TABLE IF EXISTS time_series_data")
            cursor.execute("DROP TABLE IF EXISTS product_info")

            cursor.execute("""
           CREATE TABLE IF NOT EXISTS product_info (
               ID VARCHAR(50) PRIMARY KEY,
               product VARCHAR(200),
               category VARCHAR(100),
               subcategory VARCHAR(100),
               subsubcategory VARCHAR(100),
               brand VARCHAR(100)
           )
           """)

            cursor.execute("""
           CREATE TABLE IF NOT EXISTS time_series_data (
               ID VARCHAR(50) PRIMARY KEY,
               FOREIGN KEY (ID) REFERENCES product_info(ID)
           )
           """)

            # 날짜 컬럼 추가
            date_columns = [col for col in df.columns if col.startswith("202")]
            for date in date_columns:
                cursor.execute(f'ALTER TABLE time_series_data ADD COLUMN "{date}" INTEGER')

            print("데이터 저장 중...")
            # 제품 정보 저장
            product_data = df[["ID", "제품", "대분류", "중분류", "소분류", "브랜드"]].values.tolist()
            cursor.executemany("INSERT INTO product_info VALUES (%s, %s, %s, %s, %s, %s)", product_data)

            # 시계열 데이터 저장
            print("시계열 데이터 저장 중...")
            for _, row in tqdm(df.iterrows(), total=len(df)):
                columns = ["ID"] + [f'"{date}"' for date in date_columns]
                values = [row["ID"]] + [row[date] if pd.notna(row[date]) else None for date in date_columns]
                cursor.execute(f"INSERT INTO time_series_data ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(values))})", values)

            print("데이터베이스 변환이 완료되었습니다!")

    except Exception as e:
        print(f"오류가 발생했습니다: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    args = get_db_args()
    csv_to_postgresql("train.csv", args)
