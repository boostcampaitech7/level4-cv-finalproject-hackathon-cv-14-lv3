import pandas as pd


def rename_category_columns(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path, sep=";")
    df = df.rename(columns={"Mai Category": "Main", "Subcategory 1": "Sub1", "Subcategory 2": "Sub2", "Subcategory 3": "Sub3"})
    df = df.dropna(subset=["Sub2", "Sub3"])
    df.insert(0, "ID", range(len(df)))
    return df[["ID", "Main", "Sub1", "Sub2", "Sub3"]]


if __name__ == "__main__":
    df = rename_category_columns("amazon_categories.csv")
    df.to_csv("train/amazon_categories.csv", index=False)
