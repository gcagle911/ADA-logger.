import os
import pandas as pd
import json
from datetime import datetime, timedelta, UTC
import glob
from typing import List, Dict, Any  # type: ignore

# Optional GCS sync for generated files
try:
    import gcs_utils  # type: ignore
except Exception:
    gcs_utils = None

DATA_FOLDER = "render_app/data"
EXPECTED_ASSET_PAIR = None  # When set, filter rows to this asset (e.g., ADA-USD)

def process_csv_to_json():
    """
    Process all CSV files in the data folder and generate JSON files for chart consumption.
    Creates:
    - historical.json: Complete dataset
    - recent.json: Last 24 hours of data
    - metadata.json: Dataset metadata
    - index.json: Index of available data
    - output_YYYY-MM-DD.json: Daily files
    """
    try:
        os.makedirs(DATA_FOLDER, exist_ok=True)
        
        # Find all CSV files
        csv_pattern = os.path.join(DATA_FOLDER, "*.csv")
        csv_files = sorted(glob.glob(csv_pattern))
        
        if not csv_files:
            print("⚠️ No CSV files found for processing")
            return
        
        print(f"📊 Processing {len(csv_files)} CSV files...")
        
        # Read and combine all CSV data
        all_dataframes = []
        
        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file)
                if not df.empty:
                    # Filter to expected asset if configured and column is present
                    try:
                        if EXPECTED_ASSET_PAIR and 'asset' in df.columns:
                            df = df[df['asset'] == EXPECTED_ASSET_PAIR]
                            if df.empty:
                                print(f"⏭️  Skip {csv_file}: no rows for {EXPECTED_ASSET_PAIR}")
                                continue
                    except Exception:
                        pass
                    # Ensure timestamp is datetime with proper ISO8601 parsing
                    df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601', utc=True)
                    all_dataframes.append(df)
                    print(f"✅ Loaded {csv_file}: {len(df)} records")
            except Exception as e:
                print(f"❌ Error loading {csv_file}: {e}")
                continue
        
        if not all_dataframes:
            print("❌ No valid data found in CSV files")
            return
        
        # Combine all data
        combined_df = pd.concat(all_dataframes, ignore_index=True)
        combined_df = combined_df.sort_values('timestamp').reset_index(drop=True)
        
        print(f"📈 Combined dataset: {len(combined_df)} total records")
        
        # Generate different JSON outputs
        _generate_historical_json(combined_df)
        _generate_recent_json(combined_df)
        _generate_daily_json_files(combined_df)
        _generate_metadata(combined_df, csv_files)
        _generate_index(csv_files)
        
        print("✅ JSON processing completed successfully!")
        
    except Exception as e:
        print(f"❌ Error in process_csv_to_json: {e}")
        raise

def _load_json_list(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'r') as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except Exception:
        return []


def _merge_by_key(lists: List[List[Dict[str, Any]]], key: str = "time") -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for records in lists:
        for rec in records:
            k = rec.get(key)
            if k is None:
                continue
            merged[k] = rec
    try:
        return sorted(merged.values(), key=lambda r: r.get(key, ""))
    except Exception:
        return list(merged.values())

def _generate_historical_json(df):
    """Generate complete historical data JSON - RESAMPLED TO 1-MINUTE INTERVALS"""
    try:
        # CRITICAL FIX: Resample to 1-minute intervals instead of using every second
        df_copy = df.copy()
        df_copy.set_index('timestamp', inplace=True)
        
        # Resample to 1-minute OHLC for price, last values for bid/ask, mean for spreads, sum for volume
        resampled = df_copy.resample('1min').agg({
            'price': 'last',           # Use last price in the minute
            'bid': 'last',             # Use last bid in the minute  
            'ask': 'last',             # Use last ask in the minute
            'spread': 'mean',          # Average spread over the minute
            'spread_avg_L5_pct': 'mean',  # Average L5 spread percentage
            'volume': 'sum'            # Sum volume over the minute
        }).dropna()
        
        # Convert to chart format
        chart_data = []
        for timestamp, row in resampled.iterrows():
            chart_data.append({
                "time": timestamp.isoformat(),
                "price": float(row['price']),
                "bid": float(row['bid']),
                "ask": float(row['ask']),
                "spread": float(row['spread']),
                "spread_pct": float(row['spread_avg_L5_pct']),
                "volume": float(row['volume'])
            })
        
        output_path = os.path.join(DATA_FOLDER, "historical.json")
        # Build strictly from CSVs to avoid cross-contamination
        with open(output_path, 'w') as f:
            json.dump(chart_data, f, indent=2)
        
        # Optional: upload to GCS
        try:
            if gcs_utils and gcs_utils.is_gcs_enabled():
                gcs_utils.upload_if_exists(output_path, output_path, content_type="application/json")
        except Exception as _:
            pass
        
        print(f"📊 Generated historical.json: {len(chart_data)} records")
        
    except Exception as e:
        print(f"❌ Error generating historical.json: {e}")

def _generate_recent_json(df):
    """Generate last 24 hours of data JSON - RESAMPLED TO 1-MINUTE INTERVALS"""
    try:
        # Get last 24 hours
        now = datetime.now(UTC)
        cutoff_time = now - timedelta(hours=24)
        
        recent_df = df[df['timestamp'] >= cutoff_time].copy()
        
        # CRITICAL FIX: Resample to 1-minute intervals instead of using every second
        recent_df.set_index('timestamp', inplace=True)
        
        # Resample to 1-minute intervals
        resampled = recent_df.resample('1min').agg({
            'price': 'last',           # Use last price in the minute
            'bid': 'last',             # Use last bid in the minute  
            'ask': 'last',             # Use last ask in the minute
            'spread': 'mean',          # Average spread over the minute
            'spread_avg_L5_pct': 'mean',  # Average L5 spread percentage
            'volume': 'sum'            # Sum volume over the minute
        }).dropna()
        
        # Convert to chart format
        chart_data = []
        for timestamp, row in resampled.iterrows():
            chart_data.append({
                "time": timestamp.isoformat(),
                "price": float(row['price']),
                "bid": float(row['bid']),
                "ask": float(row['ask']),
                "spread": float(row['spread']),
                "spread_pct": float(row['spread_avg_L5_pct']),
                "volume": float(row['volume'])
            })
        
        output_path = os.path.join(DATA_FOLDER, "recent.json")
        # Build strictly from CSVs, then enforce 24h window
        merged = chart_data
        # Enforce 24h window: filter by now-24h
        now = datetime.now(UTC)
        cutoff_time = now - timedelta(hours=24)
        def _iso_to_dt(s):
            try:
                return datetime.fromisoformat(s.replace("Z", "+00:00"))
            except Exception:
                return now
        merged = [r for r in merged if _iso_to_dt(r.get("time", "")) >= cutoff_time]
        with open(output_path, 'w') as f:
            json.dump(merged, f, indent=2)
        
        # Optional: upload to GCS
        try:
            if gcs_utils and gcs_utils.is_gcs_enabled():
                gcs_utils.upload_if_exists(output_path, output_path, content_type="application/json")
        except Exception as _:
            pass
        
        print(f"⚡ Generated recent.json: {len(chart_data)} records (last 24h)")
        
    except Exception as e:
        print(f"❌ Error generating recent.json: {e}")

def _generate_daily_json_files(df):
    """Generate daily JSON files"""
    try:
        # Group by date
        df['date'] = df['timestamp'].dt.date
        
        for date, group in df.groupby('date'):
            # Resample to 1-minute intervals for daily files
            group_resampled = group.set_index('timestamp').resample('1min').agg({
                'price': 'last',
                'bid': 'last', 
                'ask': 'last',
                'spread': 'mean',
                'spread_avg_L5_pct': 'mean',
                'volume': 'sum'
            }).ffill().dropna()
            
            # Convert to chart format
            chart_data = []
            for timestamp, row in group_resampled.iterrows():
                chart_data.append({
                    "time": timestamp.isoformat(),
                    "price": float(row['price']),
                    "bid": float(row['bid']),
                    "ask": float(row['ask']),
                    "spread": float(row['spread']),
                    "spread_pct": float(row['spread_avg_L5_pct']),
                    "volume": float(row['volume'])
                })
            
            if chart_data:
                filename = f"output_{date}.json"
                output_path = os.path.join(DATA_FOLDER, filename)
                # Build strictly from CSVs for daily files
                with open(output_path, 'w') as f:
                    json.dump(chart_data, f, indent=2)
                
                # Optional: upload to GCS
                try:
                    if gcs_utils and gcs_utils.is_gcs_enabled():
                        gcs_utils.upload_if_exists(output_path, output_path, content_type="application/json")
                except Exception as _:
                    pass
                
                print(f"📅 Generated {filename}: {len(chart_data)} records")
        
    except Exception as e:
        print(f"❌ Error generating daily JSON files: {e}")

def _generate_metadata(df, csv_files):
    """Generate metadata about the dataset"""
    try:
        metadata = {
            "generated_at": datetime.now(UTC).isoformat(),
            "total_records": len(df),
            "date_range": {
                "start": df['timestamp'].min().isoformat(),
                "end": df['timestamp'].max().isoformat()
            },
            "csv_files_processed": len(csv_files),
            "assets": sorted(list(set(df['asset'].dropna().unique()))) if 'asset' in df.columns else ([EXPECTED_ASSET_PAIR] if EXPECTED_ASSET_PAIR else []),
            "exchanges": list(sorted(set(df['exchange'].dropna().unique()))) if 'exchange' in df.columns else [],
            "data_points": {
                "price": "Mid price between bid/ask",
                "bid": "Best bid price",
                "ask": "Best ask price", 
                "spread": "Bid-ask spread",
                "spread_pct": "Spread as percentage",
                "volume": "Order book volume"
            },
            "update_frequency": "1 second",
            "file_rotation": "8 hour blocks"
        }
        
        output_path = os.path.join(DATA_FOLDER, "metadata.json")
        with open(output_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Optional: upload to GCS
        try:
            if gcs_utils and gcs_utils.is_gcs_enabled():
                gcs_utils.upload_if_exists(output_path, output_path, content_type="application/json")
        except Exception as _:
            pass
        
        print(f"📋 Generated metadata.json")
        
    except Exception as e:
        print(f"❌ Error generating metadata: {e}")

def _generate_index(csv_files):
    """Generate index of available data files"""
    try:
        # Get all JSON files that were generated
        json_files = []
        
        # List daily output files
        daily_pattern = os.path.join(DATA_FOLDER, "output_*.json")
        daily_files = [os.path.basename(f) for f in glob.glob(daily_pattern)]
        
        index_data = {
            "generated_at": datetime.now(UTC).isoformat(),
            "csv_sources": [os.path.basename(f) for f in csv_files],
            "daily_files": sorted(daily_files),
            "chart_files": [
                "historical.json",
                "recent.json"  
            ],
            "metadata_files": [
                "metadata.json",
                "index.json"
            ]
        }
        
        output_path = os.path.join(DATA_FOLDER, "index.json")
        with open(output_path, 'w') as f:
            json.dump(index_data, f, indent=2)
        
        # Optional: upload to GCS
        try:
            if gcs_utils and gcs_utils.is_gcs_enabled():
                gcs_utils.upload_if_exists(output_path, output_path, content_type="application/json")
        except Exception as _:
            pass
        
        print(f"🗂️ Generated index.json")
        
    except Exception as e:
        print(f"❌ Error generating index: {e}")

if __name__ == "__main__":
    process_csv_to_json()