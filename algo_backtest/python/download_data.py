import pandas as pd

RAW_PATH = "../data/raw/nifty50.csv"
PROCESSED_PATH = "../data/processed/nifty50_clean.csv"

def load_and_clean_data():
    df = pd.read_csv(RAW_PATH)

    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date")
    df = df[["Date", "Close"]]
    df = df.dropna()

    df.to_csv(PROCESSED_PATH, index=False)

    print("Cleaned data saved to:", PROCESSED_PATH)
    print("Total rows:", len(df))

if __name__ == "__main__":
    load_and_clean_data()
