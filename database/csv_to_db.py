import pandas as pd
import psycopg2
from config import get_db_args
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT, AsIs
from tqdm import tqdm


def csv_to_postgresql(csv_path: str, args) -> None:
    print("CSV 파일 읽는 중...")
    df = pd.read_csv(csv_path)

    conn = psycopg2.connect(dbname=args.dbname, user=args.user, password=args.password, host=args.host, port=args.port)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

    try:
        with conn.cursor() as cursor:
            print("테이블 생성 중...")
            cursor.execute("DROP TABLE IF EXISTS time_series_data CASCADE")
            cursor.execute("DROP TABLE IF EXISTS product_info CASCADE")

            # Primary Key를 따로 생성
            df["ID"] = range(len(df))

            cursor.execute(f"""
           CREATE TABLE product_info (
               ID INTEGER PRIMARY KEY,
               Main VARCHAR(100),
               Sub1 VARCHAR(100),
               Sub2 VARCHAR(100),
               Sub3 VARCHAR(100)
           );
           ALTER TABLE product_info OWNER TO {args.user};
           """)

            cursor.execute(f"""
           CREATE TABLE time_series_data (
               ID INTEGER PRIMARY KEY,
               FOREIGN KEY (ID) REFERENCES product_info(ID)
           );
           ALTER TABLE time_series_data OWNER TO {args.user};
           """)

            # 날짜 컬럼 추가
            date_columns = [col for col in df.columns if col.startswith("202")]
            for date in date_columns:
                cursor.execute(f'ALTER TABLE time_series_data ADD COLUMN "{date}" INTEGER')

            print("데이터 저장 중...")
            # 제품 정보 저장
            product_data = df[["ID", "Main", "Sub1", "Sub2", "Sub3"]].values.tolist()
            cursor.executemany("INSERT INTO product_info VALUES (%s, %s, %s, %s, %s)", product_data)

            # 시계열 데이터 저장
            print("시계열 데이터 저장 중...")
            for _, row in tqdm(df.iterrows(), total=len(df)):
                columns = ["ID"] + [f'"{date}"' for date in date_columns]
                values = [row["ID"]] + [row[date] if pd.notna(row[date]) else None for date in date_columns]
                query = "INSERT INTO time_series_data (%s) VALUES %s"
                cursor.execute(query, (AsIs(", ".join(columns)), tuple(values)))

            print("데이터베이스 변환이 완료되었습니다!")

    except Exception as e:
        print(f"오류가 발생했습니다: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    args = get_db_args()
    csv_to_postgresql("train.csv", args)
