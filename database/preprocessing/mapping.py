import pandas as pd


def rename_category_columns(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path, sep=";")
    df = df.rename(columns={"ID": "id", "Main Category": "main", "Subcategory 1": "sub1", "Subcategory 2": "sub2", "Subcategory 3": "sub3"})
    df = df.dropna(subset=["sub2", "sub3"])
    df.insert(0, "ID", range(len(df)))

    # Main, Sub1, Sub2, Sub3 컬럼을 기준으로 중복 제거
    df = df.drop_duplicates(subset=["main", "sub1", "sub2", "sub3"])

    return df[["id", "main", "sub1", "sub2", "sub3"]]


if __name__ == "__main__":
    df = rename_category_columns("origin/amazon_categories.csv")
    df.to_csv("train/amazon_categories.csv", index=False)
