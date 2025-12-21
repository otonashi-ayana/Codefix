from data_loader import load_data
from analyzer import summarize_sales
from visualizer import plot_sales

if __name__ == "__main__":
    df = load_data("data.csv")
    summary = summarize_sales(df)
    print("Summary:")
    print(summary)
    plot_sales(summary)
