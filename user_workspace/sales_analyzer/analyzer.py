import pandas as pd

def summarize_sales(df):
    grouped = df.groupby("region")["sales"].sum().reset_index()
    grouped = grouped.sort_values("sales", ascending=False)
    return grouped