import os
import pandas as pd
from datetime import datetime

DATA_FOLDER = "data"

def process_all_csvs():
    # STEP 1: Find all CSVs
    files = [f for f in os.listdir(DATA_FOLDER) if f.endswith(".csv")]
    grouped = {}

    # STEP 2: Group them by day
    for f in files:
        try:
            date_part = f.split("_")[0]
            grouped.setdefault(date_part, []).append(f)
        except:
            continue

    all_days = []

    for date_str, file_list in grouped.items():
        file_list.sort()
        dfs = []
        for fname in file_list:
            path = os.path.join(DATA_FOLDER, fname)
            try:
                df = pd.read_csv(path)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                dfs.append(df)
            except:
                continue

        if not dfs:
            continue

        full_df = pd.concat(dfs).sort_values("timestamp")
        full_df.set_index("timestamp", inplace=True)

        # STEP 3: Downsample to 1-minute
        ohlc = full_df["price"].resample("1min").ohlc()
        spread_mean = full_df["spread_avg_L20_pct"].resample("1min").mean()

        result = pd.concat([ohlc, spread_mean.rename("spread_avg_L20_pct")], axis=1)

        # STEP 4: Add MAs
        result["ma50"] = result["spread_avg_L20_pct"].rolling(50).mean()
        result["ma100"] = result["spread_avg_L20_pct"].rolling(100).mean()
        result["ma200"] = result["spread_avg_L20_pct"].rolling(200).mean()

        result.dropna(inplace=True)
        result.reset_index(inplace=True)

        # STEP 5: Write JSON file
        output_file = f"output_{date_str}.json"
        output_path = os.path.join(DATA_FOLDER, output_file)
        result.to_json(output_path, orient="records", date_format="iso")
        all_days.append(output_file)

    # STEP 6: Write index.json
    index_path = os.path.join(DATA_FOLDER, "index.json")
    with open(index_path, "w") as f:
        f.write("{\"days\": " + str(all_days).replace("'", "\"") + "}")

if __name__ == "__main__":
    process_all_csvs()
