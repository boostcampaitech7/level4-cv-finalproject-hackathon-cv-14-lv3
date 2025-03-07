import pandas as pd


def rename_weekly_columns(file_path: str):
    # CSV 파일 읽기
    df = pd.read_csv(file_path)

    # 컬럼명 변경을 위한 매핑 딕셔너리 생성
    rename_dict = {}
    for col in df.columns:
        if col == "ID":  # ID 컬럼은 변경하지 않음
            continue

        year, week = col.split("-")
        new_col = f"{year}_w{week.zfill(2)}"  # 하이픈을 언더스코어로 변경
        rename_dict[col] = new_col

    # 컬럼명 변경
    df = df.rename(columns=rename_dict)
    df = df.rename(columns={"ID": "id"})

    # 변경된 CSV 파일 저장
    output_path = "weekly_sales_renamed.csv"
    df.to_csv(output_path, index=False)
    print(f"파일이 {output_path}로 저장되었습니다.")

    # 변경된 컬럼명 출력
    print("\n변경된 컬럼명 예시:")
    print(list(df.columns)[:5])  # 처음 5개 컬럼만 출력

    # Supabase 테이블 생성 SQL문 생성
    sql_columns = ["id INTEGER PRIMARY KEY REFERENCES product_info(id)"]
    sql_columns.extend([f'"{col}" INTEGER' for col in df.columns if col != "ID"])

    sql = "CREATE TABLE weekly_sales (\n    " + ",\n    ".join(sql_columns) + "\n);"
    print("\nSupabase 테이블 생성 SQL:")
    print(sql)


# 함수 실행
rename_weekly_columns("weekly_sales.csv")
