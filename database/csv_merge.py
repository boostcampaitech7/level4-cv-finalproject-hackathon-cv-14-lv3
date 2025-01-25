import numpy as np
import pandas as pd


def process_and_adjust_data():
    # Initial data processing
    train_df = pd.read_csv("train/train.csv")
    categories_df = pd.read_csv("train/amazon_categories.csv")

    columns_to_drop = ["제품", "대분류", "중분류", "소분류", "브랜드"]
    train_df = train_df.drop(columns=columns_to_drop)

    # Generate initial dummy rows
    required_rows = 22439 - len(train_df)
    date_columns = [col for col in train_df.columns if col not in ["ID"]]

    if required_rows > 0:
        dummy_data = {"ID": range(max(train_df["ID"]) + 1, max(train_df["ID"]) + required_rows + 1)}
        for col in date_columns:
            mean = train_df[col].mean()
            std = train_df[col].std()
            dummy_data[col] = np.random.normal(mean, std, required_rows).astype(int)

        dummy_df = pd.DataFrame(dummy_data)
        train_df = pd.concat([train_df, dummy_df], ignore_index=True)

    # Merge with categories
    categories_df.columns = ["Main", "Sub1", "Sub2", "Sub3"]
    merged_df = pd.concat([categories_df, train_df.drop(columns=["ID"])], axis=1)
    merged_df.to_csv("processed_data.csv", index=False)

    # Adjust distribution
    time_cols = [col for col in merged_df.columns if col.startswith("202")]
    final_df = merged_df.copy()

    orig_stats = merged_df.iloc[:15891][time_cols].agg(["mean", "std"]).transpose()

    for col in time_cols:
        mean, std = orig_stats.loc[col, ["mean", "std"]]
        new_values = np.random.normal(mean, std, len(merged_df.iloc[15891:]))
        new_values = np.abs(new_values).astype(int)
        zero_mask = np.random.random(len(merged_df.iloc[15891:])) < 0.6
        new_values[zero_mask] = 0
        final_df.loc[15891:, col] = new_values

    final_df.to_csv("train.csv", index=False)
    return final_df


# Execute and print statistics
df = process_and_adjust_data()
time_cols = [col for col in df.columns if col.startswith("202")]

print("\nOriginal data statistics (first 15891 rows):")
print(df.iloc[:15891][time_cols].describe())
print("\nGenerated data statistics (remaining rows):")
print(df.iloc[15891:][time_cols].describe())
