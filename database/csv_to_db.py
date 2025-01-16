import sqlite3

import pandas as pd


def csv_to_sqlite(csv_path: str) -> None:
    """
    CSV 파일을 SQLite 데이터베이스로 변환하는 함수

    Args:
        csv_path: CSV 파일 경로
    """
    # CSV 파일 읽기
    df = pd.read_csv(csv_path)

    # SQLite 데이터베이스 연결
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()

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
            date DATE,
            value INTEGER,
            FOREIGN KEY (ID) REFERENCES product_info(ID)
        )
        """)

        # 제품 정보 데이터 저장
        product_data = df[["ID", "제품", "대분류", "중분류", "소분류", "브랜드"]].values.tolist()
        cursor.executemany("INSERT INTO product_info VALUES (?, ?, ?, ?, ?, ?)", product_data)

        # 시계열 데이터 삽입
        date_columns = [col for col in df.columns if col.startswith("202")]
        timeseries_data = []

        for _, row in df.iterrows():
            for date in date_columns:
                if pd.notna(row[date]):
                    timeseries_data.append((row["ID"], date, int(row[date])))

        cursor.executemany("INSERT INTO time_series_data VALUES (?, ?, ?)", timeseries_data)

        # 변경사항 저장
        conn.commit()


if __name__ == "__main__":
    csv_to_sqlite("train.csv")
