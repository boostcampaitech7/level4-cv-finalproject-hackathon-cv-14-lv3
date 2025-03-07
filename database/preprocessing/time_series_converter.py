from datetime import datetime

import pandas as pd


def rename_columns(df):
    # id 컬럼은 제외하고 날짜 컬럼만 변경
    date_columns = [col for col in df.columns if col != "id"]

    # 새로운 컬럼명 매핑 생성
    new_columns = {}
    for col in date_columns:
        # 날짜 문자열을 datetime 객체로 변환
        date_obj = datetime.strptime(col, "%Y-%m-%d")
        # 새로운 형식으로 변환 (YY_MM_DD)
        new_col = date_obj.strftime("%y_%m_%d")
        new_columns[col] = new_col

    # id 컬럼은 그대로 유지
    new_columns["id"] = "id"

    # 컬럼명 변경
    df = df.rename(columns=new_columns)
    return df


# CSV 파일 읽기
df = pd.read_csv("time_series_data.csv")

# 컬럼명 변경 함수 적용
df_renamed = rename_columns(df)

# 변경된 CSV 파일 저장
df_renamed.to_csv("time_series_data_renamed.csv", index=False)
