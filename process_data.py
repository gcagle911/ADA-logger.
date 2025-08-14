import os
import pandas as pd
import json
from datetime import datetime, timedelta, UTC
import glob
from typing import List, Dict, Optional

# Optional GCS sync for generated files
try:
    import gcs_utils  # type: ignore
except Exception:
    gcs_utils = None

DATA_FOLDER = "render_app/data"

# Limits for JSON outputs
RECENT_MAX_POINTS = 24 * 60  # 1 point per minute for last 24h
HISTORICAL_MAX_POINTS = 200_000  # safety cap

def _merge_by_time(existing: List[Dict], new: List[Dict], *, limit: Optional[int] = None) -> List[Dict]:
    """Merge two lists of records keyed by 'time', de-duplicate, sort asc, and trim to limit."""
    merged = {}
    for rec in existing or []:
        t = rec.get("time")
        if t is not None:
            merged[t] = rec
    for rec in new or []:
        t = rec.get("time")
        if t is not None:
            merged[t] = rec
    # Sort by ISO8601 time ascending
    items = list(merged.items())
    items.sort(key=lambda kv: kv[0])
    records = [kv[1] for kv in items]
    if limit is not None and len(records) > limit:
        records = records[-limit:]
    return records

def process_csv_to_json(bucket_name: Optional[str] = None):
    """
    Process all CSV files in the data folder and generate JSON files for chart consumption.
    Creates:
    - historical.json: Complete dataset
    - recent.json: Last 24 hours of data
    - metadata.json: Dataset metadata
    - index.json: Index of available data
    - archive/1min/YYYY-MM-DD.json: Daily files (and backward-compatible output_YYYY-MM-DD.json)
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
        _generate_historical_json(combined_df, bucket_name=bucket_name)
        _generate_recent_json(combined_df, bucket_name=bucket_name)
        _generate_daily_json_files(combined_df, bucket_name=bucket_name)
        _generate_metadata(combined_df, csv_files, bucket_name=bucket_name)
        _generate_index(csv_files, bucket_name=bucket_name)
        
        print("✅ JSON processing completed successfully!")
        
    except Exception as e:
        print(f"❌ Error in process_csv_to_json: {e}")
        raise

def _generate_historical_json(df, *, bucket_name: Optional[str] = None):
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
        new_chart_data = []
        for timestamp, row in resampled.iterrows():
            new_chart_data.append({
                "time": timestamp.isoformat(),
                "price": float(row['price']),
                "bid": float(row['bid']),
                "ask": float(row['ask']),
                "spread": float(row['spread']),
                "spread_pct": float(row['spread_avg_L5_pct']),
                "volume": float(row['volume'])
            })
        
        output_path = os.path.join(DATA_FOLDER, "historical.json")
        # GCS-first merge
        try:
            if gcs_utils and gcs_utils.is_gcs_enabled(bucket_name=bucket_name):
                gcs_blob = output_path
                gcs_utils.download_from_gcs(gcs_blob, output_path, bucket_name=bucket_name)
        except Exception:
            pass

        existing_data: List[Dict] = []
        try:
            if os.path.exists(output_path):
                with open(output_path, 'r') as rf:
                    existing_data = json.load(rf)
        except Exception:
            existing_data = []

        merged = _merge_by_time(existing_data, new_chart_data, limit=HISTORICAL_MAX_POINTS)
        if gcs_utils:
            gcs_utils.write_json_records(merged, output_path)
        else:
            with open(output_path, 'w') as f:
                json.dump(merged, f, indent=2, allow_nan=False)
        
        # Optional: upload to GCS
        try:
            if gcs_utils and gcs_utils.is_gcs_enabled(bucket_name=bucket_name):
                gcs_utils.upload_to_gcs(output_path, output_path, bucket_name=bucket_name, content_type="application/json")
        except Exception as _:
            pass
        
        print(f"📊 Generated historical.json: {len(merged)} records")
        
    except Exception as e:
        print(f"❌ Error generating historical.json: {e}")

def _generate_recent_json(df, *, bucket_name: Optional[str] = None):
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
        new_chart_data = []
        for timestamp, row in resampled.iterrows():
            new_chart_data.append({
                "time": timestamp.isoformat(),
                "price": float(row['price']),
                "bid": float(row['bid']),
                "ask": float(row['ask']),
                "spread": float(row['spread']),
                "spread_pct": float(row['spread_avg_L5_pct']),
                "volume": float(row['volume'])
            })
        
        output_path = os.path.join(DATA_FOLDER, "recent.json")
        # GCS-first merge
        try:
            if gcs_utils and gcs_utils.is_gcs_enabled(bucket_name=bucket_name):
                gcs_blob = output_path
                gcs_utils.download_from_gcs(gcs_blob, output_path, bucket_name=bucket_name)
        except Exception:
            pass

        existing_data: List[Dict] = []
        try:
            if os.path.exists(output_path):
                with open(output_path, 'r') as rf:
                    existing_data = json.load(rf)
        except Exception:
            existing_data = []

        merged = _merge_by_time(existing_data, new_chart_data, limit=RECENT_MAX_POINTS)
        if gcs_utils:
            gcs_utils.write_json_records(merged, output_path)
        else:
            with open(output_path, 'w') as f:
                json.dump(merged, f, indent=2, allow_nan=False)
        
        # Optional: upload to GCS
        try:
            if gcs_utils and gcs_utils.is_gcs_enabled(bucket_name=bucket_name):
                gcs_utils.upload_to_gcs(output_path, output_path, bucket_name=bucket_name, content_type="application/json")
        except Exception as _:
            pass
        
        print(f"⚡ Generated recent.json: {len(merged)} records (last 24h)")
        
    except Exception as e:
        print(f"❌ Error generating recent.json: {e}")

def _generate_daily_json_files(df, *, bucket_name: Optional[str] = None):
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
            new_chart_data = []
            for timestamp, row in group_resampled.iterrows():
                new_chart_data.append({
                    "time": timestamp.isoformat(),
                    "price": float(row['price']),
                    "bid": float(row['bid']),
                    "ask": float(row['ask']),
                    "spread": float(row['spread']),
                    "spread_pct": float(row['spread_avg_L5_pct']),
                    "volume": float(row['volume'])
                })
            
            if new_chart_data:
                # Primary archive path
                archive_dir = os.path.join(DATA_FOLDER, "archive", "1min")
                os.makedirs(archive_dir, exist_ok=True)
                archive_filename = f"{date}.json"
                archive_path = os.path.join(archive_dir, archive_filename)

                # GCS-first merge for archive
                try:
                    if gcs_utils and gcs_utils.is_gcs_enabled(bucket_name=bucket_name):
                        gcs_blob = archive_path
                        gcs_utils.download_from_gcs(gcs_blob, archive_path, bucket_name=bucket_name)
                except Exception:
                    pass

                existing_data: List[Dict] = []
                try:
                    if os.path.exists(archive_path):
                        with open(archive_path, 'r') as rf:
                            existing_data = json.load(rf)
                except Exception:
                    existing_data = []

                merged = _merge_by_time(existing_data, new_chart_data, limit=None)
                if gcs_utils:
                    gcs_utils.write_json_records(merged, archive_path)
                else:
                    with open(archive_path, 'w') as f:
                        json.dump(merged, f, indent=2, allow_nan=False)

                # Backward-compatible filename
                legacy_filename = f"output_{date}.json"
                legacy_path = os.path.join(DATA_FOLDER, legacy_filename)
                try:
                    if gcs_utils:
                        gcs_utils.write_json_records(merged, legacy_path)
                    else:
                        with open(legacy_path, 'w') as f:
                            json.dump(merged, f, indent=2, allow_nan=False)
                except Exception:
                    pass
                
                # Upload to GCS
                try:
                    if gcs_utils and gcs_utils.is_gcs_enabled(bucket_name=bucket_name):
                        gcs_utils.upload_to_gcs(archive_path, archive_path, bucket_name=bucket_name, content_type="application/json")
                        gcs_utils.upload_to_gcs(legacy_path, legacy_path, bucket_name=bucket_name, content_type="application/json")
                except Exception:
                    pass
                
                print(f"📅 Generated {archive_filename}: {len(merged)} records")
         
    except Exception as e:
        print(f"❌ Error generating daily JSON files: {e}")

def _generate_metadata(df, csv_files, *, bucket_name: Optional[str] = None):
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
            "assets": ["ADA-USD"],
            "exchanges": ["Coinbase"],
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
        if gcs_utils:
            gcs_utils.write_json_records([metadata], output_path)
            # rewrite as object form (not array) for compatibility
            try:
                with open(output_path, 'w') as f:
                    json.dump(metadata, f, indent=2, allow_nan=False)
            except Exception:
                pass
        else:
            with open(output_path, 'w') as f:
                json.dump(metadata, f, indent=2)
        
        # Optional: upload to GCS
        try:
            if gcs_utils and gcs_utils.is_gcs_enabled(bucket_name=bucket_name):
                gcs_utils.upload_to_gcs(output_path, output_path, bucket_name=bucket_name, content_type="application/json")
        except Exception as _:
            pass
        
        print(f"📋 Generated metadata.json")
        
    except Exception as e:
        print(f"❌ Error generating metadata: {e}")

def _generate_index(csv_files, *, bucket_name: Optional[str] = None):
    """Generate index of available data files"""
    try:
        # Get all JSON files that were generated
        json_files = []
        
        # List daily output files
        daily_pattern_legacy = os.path.join(DATA_FOLDER, "output_*.json")
        daily_files_legacy = [os.path.basename(f) for f in glob.glob(daily_pattern_legacy)]
        daily_pattern_archive = os.path.join(DATA_FOLDER, "archive", "1min", "*.json")
        daily_files_archive = [
            os.path.join("archive/1min", os.path.basename(f)) for f in glob.glob(daily_pattern_archive)
        ]
        
        index_data = {
            "generated_at": datetime.now(UTC).isoformat(),
            "csv_sources": [os.path.basename(f) for f in csv_files],
            "daily_files": sorted(daily_files_legacy + daily_files_archive),
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
        if gcs_utils:
            gcs_utils.write_json_records([index_data], output_path)
            # rewrite as object form for compatibility
            try:
                with open(output_path, 'w') as f:
                    json.dump(index_data, f, indent=2, allow_nan=False)
            except Exception:
                pass
        else:
            with open(output_path, 'w') as f:
                json.dump(index_data, f, indent=2)
        
        # Optional: upload to GCS
        try:
            if gcs_utils and gcs_utils.is_gcs_enabled(bucket_name=bucket_name):
                gcs_utils.upload_to_gcs(output_path, output_path, bucket_name=bucket_name, content_type="application/json")
        except Exception as _:
            pass
        
        print(f"🗂️ Generated index.json")
        
    except Exception as e:
        print(f"❌ Error generating index: {e}")

if __name__ == "__main__":
    process_csv_to_json()

def generate_all_jsons(bucket_name: Optional[str] = None):
    """Helper to generate all JSON outputs with optional multi-bucket routing."""
    return process_csv_to_json(bucket_name=bucket_name)