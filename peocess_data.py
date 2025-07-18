# BTC Data Processing - Enhanced with Historical Data Management
# Updated: 2025-07-10 - Fixed timestamp checking and added comprehensive debugging
# This version includes hybrid data loading (recent.json + historical.json)

import pandas as pd
import os
import json
from datetime import datetime, timedelta
import glob

DATA_FOLDER = "render_app/data"

def load_all_historical_data():
    """Load and combine all CSV files into a single chronological dataset"""
    print(f"🔍 Looking for CSV files in: {DATA_FOLDER}")
    csv_files = glob.glob(os.path.join(DATA_FOLDER, "*.csv"))
    
    if not csv_files:
        print("❌ No CSV files found")
        print(f"🔍 Checked path: {os.path.join(DATA_FOLDER, '*.csv')}")
        print(f"🔍 Directory exists: {os.path.exists(DATA_FOLDER)}")
        if os.path.exists(DATA_FOLDER):
            all_files = os.listdir(DATA_FOLDER)
            print(f"🔍 All files in directory: {all_files}")
        return None
    
    print(f"📁 Found {len(csv_files)} CSV files:")
    for csv_file in sorted(csv_files):
        file_size = os.path.getsize(csv_file) if os.path.exists(csv_file) else 0
        print(f"   📄 {os.path.basename(csv_file)} ({file_size} bytes)")
    
    all_dfs = []
    for csv_file in sorted(csv_files):
        try:
            df = pd.read_csv(csv_file, parse_dates=["timestamp"])
            if not df.empty:
                all_dfs.append(df)
                # Show date range for each file
                min_time = df['timestamp'].min()
                max_time = df['timestamp'].max()
                print(f"✅ Loaded: {os.path.basename(csv_file)} ({len(df)} rows, {min_time} to {max_time})")
            else:
                print(f"⚠️ Empty file: {os.path.basename(csv_file)}")
        except Exception as e:
            print(f"❌ Error loading {csv_file}: {e}")
    
    if not all_dfs:
        print("❌ No valid data found")
        return None
    
    # Combine all data and sort chronologically
    combined_df = pd.concat(all_dfs, ignore_index=True)
    combined_df = combined_df.sort_values("timestamp")
    combined_df = combined_df.drop_duplicates(subset=["timestamp"], keep="last")
    
    # Show overall date range
    min_time = combined_df['timestamp'].min()
    max_time = combined_df['timestamp'].max()
    print(f"✅ Combined dataset: {len(combined_df)} total rows ({min_time} to {max_time})")
    return combined_df

def resample_and_calculate_mas(df):
    """Resample to 1-minute intervals and calculate MAs with full historical context"""
    if df is None or df.empty:
        return None
    
    # Set timestamp as index for resampling
    df_indexed = df.set_index("timestamp")
    df_indexed.index = pd.to_datetime(df_indexed.index)
    
    # Resample to 1-minute intervals
    df_1min = df_indexed.resample("1min").agg({
        "price": "last",
        "spread_avg_L20_pct": "mean"
    }).dropna()
    
    print(f"📊 Resampled to {len(df_1min)} 1-minute intervals")
    
    # Calculate moving averages with full historical context
    df_1min["ma_50"] = df_1min["spread_avg_L20_pct"].rolling(window=50, min_periods=1).mean()
    df_1min["ma_100"] = df_1min["spread_avg_L20_pct"].rolling(window=100, min_periods=1).mean()
    df_1min["ma_200"] = df_1min["spread_avg_L20_pct"].rolling(window=200, min_periods=1).mean()
    
    # Add data quality indicators
    df_1min["ma_50_valid"] = df_1min["spread_avg_L20_pct"].rolling(window=50).count() >= 50
    df_1min["ma_100_valid"] = df_1min["spread_avg_L20_pct"].rolling(window=100).count() >= 100
    df_1min["ma_200_valid"] = df_1min["spread_avg_L20_pct"].rolling(window=200).count() >= 200
    
    df_1min.reset_index(inplace=True)
    df_1min.rename(columns={"timestamp": "time"}, inplace=True)
    
    return df_1min

def save_recent_data(df_full):
    """Save last 24 hours of data for fast chart loading"""
    if df_full is None or df_full.empty:
        return
    
    # Get last 24 hours
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=24)
    
    df_full['time_dt'] = pd.to_datetime(df_full['time'])
    recent_data = df_full[df_full['time_dt'] >= cutoff].copy()
    recent_data = recent_data.drop(columns=['time_dt'])
    
    # Save recent data (fast loading for charts)
    recent_path = os.path.join(DATA_FOLDER, "recent.json")
    recent_data.to_json(recent_path, orient="records", date_format="iso")
    
    print(f"⚡ Saved recent.json: {len(recent_data)} records (last 24h)")
    return len(recent_data)

def should_update_historical():
    """Check if historical.json needs updating (every hour)"""
    historical_path = os.path.join(DATA_FOLDER, "historical.json")
    
    if not os.path.exists(historical_path):
        print("🔄 Historical file doesn't exist, creating...")
        return True  # Create if doesn't exist
    
    # Check if file is older than 1 hour
    try:
        file_time = datetime.fromtimestamp(os.path.getmtime(historical_path))
        now = datetime.utcnow()
        age_hours = (now - file_time).total_seconds() / 3600
        
        print(f"📅 Historical file age: {age_hours:.1f} hours (threshold: 1.0)")
        
        should_update = age_hours > 1.0
        if should_update:
            print("⏰ File is old enough, will update historical data")
        else:
            print(f"⏸️ File is recent ({age_hours:.1f}h old), skipping update")
            
        return should_update
        
    except Exception as e:
        print(f"⚠️ Error checking file timestamp: {e}, forcing update")
        return True  # Force update if timestamp check fails

def save_historical_data(df_full):
    """Save complete historical dataset (updated hourly)"""
    if df_full is None or df_full.empty:
        return
    
    # Save complete historical data
    historical_path = os.path.join(DATA_FOLDER, "historical.json")
    df_full.to_json(historical_path, orient="records", date_format="iso")
    
    # Create metadata
    metadata = {
        "generated_at": datetime.utcnow().isoformat(),
        "total_records": len(df_full),
        "date_range": {
            "start": df_full["time"].min(),
            "end": df_full["time"].max()
        },
        "ma_info": {
            "ma_50_valid_count": int(df_full["ma_50_valid"].sum()),
            "ma_100_valid_count": int(df_full["ma_100_valid"].sum()),
            "ma_200_valid_count": int(df_full["ma_200_valid"].sum())
        },
        "file_size_mb": round(os.path.getsize(historical_path) / 1024 / 1024, 2),
        "update_frequency": "hourly"
    }
    
    # Save metadata
    metadata_path = os.path.join(DATA_FOLDER, "metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2, default=str)
    
    print(f"📚 Saved historical.json: {len(df_full)} records ({metadata['file_size_mb']}MB)")
    return len(df_full)

def save_daily_jsons(df_full):
    """Create individual daily JSON files for compatibility"""
    if df_full is None or df_full.empty:
        return []
    
    df_full["date"] = pd.to_datetime(df_full["time"]).dt.date
    daily_files = []
    
    for date, day_data in df_full.groupby("date"):
        day_data_clean = day_data.drop(columns=["date"])
        
        output_file = f"output_{date}.json"
        output_path = os.path.join(DATA_FOLDER, output_file)
        
        day_data_clean.to_json(output_path, orient="records", date_format="iso")
        daily_files.append(output_file)
    
    return daily_files

def save_index_json(daily_files, recent_count, historical_count):
    """Create index file with information about all data sources"""
    index_data = {
        "data_sources": {
            "recent": {
                "file": "recent.json",
                "description": "Last 24 hours (fast loading)",
                "records": recent_count,
                "update_frequency": "every_second"
            },
            "historical": {
                "file": "historical.json", 
                "description": "Complete dataset (full history)",
                "records": historical_count,
                "update_frequency": "hourly"
            }
        },
        "daily_files": sorted(daily_files),
        "recommended_usage": {
            "fast_chart_startup": "Load /recent.json first",
            "full_historical_view": "Load /historical.json for complete data",
            "hybrid_approach": "Load recent first, then historical in background"
        },
        "last_updated": datetime.utcnow().isoformat()
    }
    
    index_path = os.path.join(DATA_FOLDER, "index.json")
    with open(index_path, "w") as f:
        json.dump(index_data, f, indent=2)
    
    print(f"📋 Saved index.json")

def process_csv_to_json():
    """
    Main function: Hybrid data processing system
    - recent.json: Updated every second (last 24h)
    - historical.json: Updated hourly (complete dataset)
    """
    print("🚀 Starting hybrid data processing...")
    
    # Step 1: Load all historical data
    df_combined = load_all_historical_data()
    if df_combined is None:
        return
    
    # Step 2: Resample and calculate MAs with full context
    df_processed = resample_and_calculate_mas(df_combined)
    if df_processed is None:
        return
    
    # Step 3: Always save recent data (fast for charts)
    recent_count = save_recent_data(df_processed)
    
    # Step 4: Check if we need to update historical data
    historical_count = len(df_processed)
    if should_update_historical():
        print("⏰ Updating historical data (hourly update)")
        historical_count = save_historical_data(df_processed)
        
        # Also update daily files when historical updates
        daily_files = save_daily_jsons(df_processed)
    else:
        print("⏸️ Skipping historical update (updated within last hour)")
        daily_files = []
    
    # Step 5: Update index
    save_index_json(daily_files, recent_count, historical_count)
    
    print("✅ Hybrid processing complete!")
    print(f"⚡ Recent data: {recent_count} records (updated every second)")
    print(f" Historical data: {historical_count} records (updated hourly)")
    print("🔄 Charts can use:")
    print("   - /recent.json for fast startup")
    print("   - /historical.json for complete data")

# Legacy function for compatibility
def process_today_only():
    """Legacy function that only processes today's data (for compatibility)"""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    files = sorted(
        f for f in os.listdir(DATA_FOLDER)
        if f.startswith(today) and f.endswith(".csv")
    )
    
    if not files:
        print(f"❌ No CSVs found for {today}")
        return
    
    latest_file = files[-1]
    csv_path = os.path.join(DATA_FOLDER, latest_file)
    print(f"📄 Processing today only: {csv_path}")
    
    df = pd.read_csv(csv_path, parse_dates=["timestamp"])
    if df.empty:
        return
    
    df.set_index("timestamp", inplace=True)
    df_1min = df.resample("1min").agg({
        "price": "last",
        "spread_avg_L20_pct": "mean"
    }).dropna()
    
    df_1min["ma_50"] = df_1min["spread_avg_L20_pct"].rolling(window=50).mean()
    df_1min["ma_100"] = df_1min["spread_avg_L20_pct"].rolling(window=100).mean()
    df_1min["ma_200"] = df_1min["spread_avg_L20_pct"].rolling(window=200).mean()
    
    df_1min.reset_index(inplace=True)
    df_1min.rename(columns={"timestamp": "time"}, inplace=True)
    
    output_path = os.path.join(DATA_FOLDER, f"output_{today}.json")
    df_1min.to_json(output_path, orient="records", date_format="iso")
    print(f"✅ Saved today's data: {output_path}")

if __name__ == "__main__":
    process_csv_to_json()
