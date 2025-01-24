import pandas as pd


def process_amazon_data(amazon_path: str, train_path: str) -> pd.DataFrame:
    # Clean Amazon Categories
    categories_df = pd.read_csv(amazon_path, sep=";")
    columns = ["Mai Category", "Subcategory 1", "Subcategory 2", "Subcategory 3"]
    cleaned_categories = categories_df[columns][categories_df["Subcategory 2"].notna() & categories_df["Subcategory 3"].notna()]
    cleaned_categories.columns = ["Main", "Sub1", "Sub2", "Sub3"]
    cleaned_categories.to_csv("cleaned_categories.csv", sep=";", index=False)

    # Process Training Data
    train_df = pd.read_csv(train_path)
    rows_to_add = len(cleaned_categories) - len(train_df)
    dummy_rows = train_df.iloc[:rows_to_add].copy()
    train_df = pd.concat([train_df, dummy_rows], ignore_index=True)
    train_df = train_df.drop(["ID", "제품", "대분류", "중분류", "소분류", "브랜드"], axis=1)

    # Merge Data
    result_df = pd.concat([cleaned_categories, train_df], axis=1)
    result_df.to_csv("processed_train.csv", index=False)
    return result_df


if __name__ == "__main__":
    df = process_amazon_data("AmazonCategories.csv", "train.csv")
