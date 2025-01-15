import sqlite3

import pandas as pd


def csv_to_sqlite(csv_path: str, db_path: str) -> None:
    """
    CSV 파일을 SQLite 데이터베이스로 변환하는 함수

    Args:
        csv_path: CSV 파일 경로
        db_path: SQLite DB 파일 저장 경로
    """
    # CSV 파일 읽기
    df = pd.read_csv(csv_path)

    # SQLite 연결
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 제품 정보 테이블 생성
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_info (
            ID VARCHAR(20) PRIMARY KEY,
            product VARCHAR(100),
            category VARCHAR(50),
            subcategory VARCHAR(50),
            subsubcategory VARCHAR(50),
            brand VARCHAR(50)
        )
        """)

        # 시계열 데이터 테이블 생성
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS time_series_data (
            ID VARCHAR(20),
            date VARCHAR(5),
            value INTEGER,
            FOREIGN KEY (ID) REFERENCES product_info(ID)
        )
        """)

        # 제품 정보 데이터 저장
        product_info = df[["ID", "제품", "대분류", "중분류", "소분류", "브랜드"]]
        product_info.to_sql("product_info", conn, if_exists="replace", index=False)

        # 시계열 데이터 처리 및 저장
        date_columns = [col for col in df.columns if col.startswith("202")]
        time_series_data = []

        for _, row in df.iterrows():
            for date in date_columns:
                if pd.notna(row[date]):
                    # 날짜에서 월-일만 추출 (YYYY-MM-DD -> MM-DD)
                    month_day = "-".join(date.split("-")[1:])
                    time_series_data.append({"ID": row["ID"], "date": month_day, "value": int(row[date])})

        # 시계열 데이터를 DataFrame으로 변환하여 저장
        time_series_df = pd.DataFrame(time_series_data)
        time_series_df.to_sql("time_series_data", conn, if_exists="replace", index=False)

        # 변경사항 저장
        conn.commit()
        print(f"데이터베이스 생성 완료: {db_path}")

    except Exception as e:
        print(f"에러 발생: {e}")
        conn.rollback()

    finally:
        # 연결 종료
        cursor.close()
        conn.close()


# 사용 예시
if __name__ == "__main__":
    csv_to_sqlite(csv_path="train.csv", db_path="database.db")

    # 데이터베이스 테스트
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # 데이터 확인
    print("\n제품 정보 샘플:")
    cursor.execute("SELECT * FROM product_info LIMIT 5")
    print(cursor.fetchall())

    print("\n시계열 데이터 샘플:")
    cursor.execute("SELECT * FROM time_series_data LIMIT 5")
    print(cursor.fetchall())

    conn.close()
