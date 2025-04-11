from csv import QUOTE_MINIMAL

import pandas as pd

amazon_df = pd.read_csv("train/amazon_categories.csv", encoding="utf-8", sep=",", quoting=QUOTE_MINIMAL)

train_df = pd.read_csv("train/sales.csv", encoding="utf-8")

date_columns = train_df.columns[6:]
sales_data = train_df[date_columns].iloc[: len(amazon_df)]

final_df = pd.concat([amazon_df[["ID", "Main", "Sub1", "Sub2", "Sub3"]], sales_data], axis=1)

final_df.to_csv("sales.csv", index=False, encoding="utf-8")
