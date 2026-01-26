import pandas as pd

def load_and_clean_data():
    # Read the raw data from the actual file
    df = pd.read_csv('../data/raw/nifty50.csv')
    
    # Clean data (for example, drop missing values)
    df = df.dropna()
    
    # Save processed data
    df.to_csv('../data/processed/nifty50_clean.csv', index=False)
    
    print("Cleaned data saved to processed folder.")

if __name__ == "__main__":
    load_and_clean_data()
