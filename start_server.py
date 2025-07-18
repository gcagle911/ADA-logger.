#!/usr/bin/env python3
"""
ADA Chart Server Startup Script
================================

This script starts the ADA data logger server and provides utilities for testing.
It includes sample data generation for development and testing purposes.
"""

import os
import sys
import json
import time
import threading
from datetime import datetime, timedelta, UTC
import pandas as pd

# Add current directory to path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from logger import app, log_data
from process_data import process_csv_to_json

DATA_FOLDER = "render_app/data"

def generate_sample_data(hours=48, interval_minutes=1):
    """Generate sample ADA data for testing the charts"""
    print(f"🔧 Generating {hours} hours of sample data...")
    
    # Create realistic sample data
    start_time = datetime.now(UTC) - timedelta(hours=hours)
    data_points = []
    
    # Starting values
    base_price = 0.85
    base_spread = 0.0005
    
    for i in range(int(hours * 60 / interval_minutes)):
        timestamp = start_time + timedelta(minutes=i * interval_minutes)
        
        # Add some realistic price movement
        price_change = (hash(str(timestamp)) % 200 - 100) / 10000  # Random-ish price movement for ADA
        price = base_price + price_change + (i * 0.0001)  # Slight upward trend
        
        # Realistic spread data
        spread_base = base_spread + (hash(str(timestamp + timedelta(seconds=30))) % 100 - 50) / 1000000
        spread_pct = spread_base * 100
        
        data_point = {
            "timestamp": timestamp.isoformat(),
            "asset": "ADA-USD",
            "exchange": "Coinbase",
            "price": round(price, 2),
            "bid": round(price - (price * spread_base / 2), 2),
            "ask": round(price + (price * spread_base / 2), 2),
            "spread": round(price * spread_base, 2),
            "volume": 50 + (hash(str(timestamp)) % 100),  # Random volume
            "spread_avg_L20": round(price * spread_base, 6),
            "spread_avg_L20_pct": round(spread_pct, 8)
        }
        data_points.append(data_point)
    
    # Group by 8-hour blocks (matching your logger's file rotation)
    grouped_data = {}
    for point in data_points:
        dt = datetime.fromisoformat(point["timestamp"])
        hour_block = (dt.hour // 8) * 8
        date_str = dt.strftime("%Y-%m-%d")
        filename = f"{date_str}_{hour_block:02d}.csv"
        
        if filename not in grouped_data:
            grouped_data[filename] = []
        grouped_data[filename].append(point)
    
    # Write CSV files
    os.makedirs(DATA_FOLDER, exist_ok=True)
    
    for filename, points in grouped_data.items():
        filepath = os.path.join(DATA_FOLDER, filename)
        
        # Convert to DataFrame and save
        df = pd.DataFrame(points)
        df.to_csv(filepath, index=False)
        print(f"📁 Created: {filepath} ({len(points)} records)")
    
    print(f"✅ Generated {len(data_points)} sample data points across {len(grouped_data)} files")
    return len(data_points)

def test_data_processing():
    """Test the data processing pipeline"""
    print("🧪 Testing data processing pipeline...")
    try:
        process_csv_to_json()
        print("✅ Data processing completed successfully!")
        
        # Check generated files
        files_to_check = ['recent.json', 'historical.json', 'metadata.json', 'index.json']
        for filename in files_to_check:
            filepath = os.path.join(DATA_FOLDER, filename)
            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                print(f"📄 {filename}: {file_size:,} bytes")
            else:
                print(f"❌ Missing: {filename}")
                
    except Exception as e:
        print(f"❌ Data processing failed: {e}")
        return False
    
    return True

def start_logger_thread():
    """Start the data logger in a separate thread"""
    print("🚀 Starting data logger thread...")
    logger_thread = threading.Thread(target=log_data, daemon=True)
    logger_thread.start()
    print("✅ Data logger started!")
    return logger_thread

def show_endpoints():
    """Display available API endpoints"""
    print("\n" + "="*60)
    print("🌐 AVAILABLE API ENDPOINTS")
    print("="*60)
    
    endpoints = {
        "Chart Data (Recommended)": [
            "/recent.json - Last 24 hours (fast loading)",
            "/historical.json - Complete dataset (full history)",
            "/metadata.json - Dataset information",
            "/index.json - Data source index"
        ],
        "Raw Data": [
            "/data.csv - Current CSV file",
            "/csv-list - List all CSV files",
            "/csv/<filename> - Download specific CSV"
        ],
        "Filtered Data": [
            "/chart-data?limit=1000 - Limited data points",
            "/chart-data?start_date=2025-01-01 - Date filtered"
        ],
        "Daily JSON": [
            "/json/output_<YYYY-MM-DD>.json - Daily data",
            "/output-latest.json - Latest daily data"
        ]
    }
    
    for category, urls in endpoints.items():
        print(f"\n📋 {category}:")
        for url in urls:
            print(f"   • {url}")
    
    port = int(os.environ.get('PORT', 10000))
    print(f"\n🔗 Base URL: http://localhost:{port}")
    print("📊 Chart Files:")
    print("   • improved_ada_chart.html - New enhanced chart")
    print("   • tradingview_style_chart.html - TradingView style")
    print("   • chart_config_example.html - Basic example")
    print("="*60)

def main():
    """Main startup function"""
    print("🚀 ADA Chart Server Startup")
    print("="*40)
    
    # Check if we have any data
    csv_files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.csv')] if os.path.exists(DATA_FOLDER) else []
    
    if not csv_files:
        print("📊 No data found. Generating sample data...")
        generate_sample_data(hours=48)  # 2 days of data
        test_data_processing()
    else:
        print(f"📁 Found {len(csv_files)} existing CSV files")
        print("🔄 Processing existing data...")
        test_data_processing()
    
    # Start the data logger
    start_logger_thread()
    
    # Wait a moment for everything to initialize
    time.sleep(2)
    
    # Show available endpoints
    show_endpoints()
    
    # Get the port that will be used
    port = int(os.environ.get('PORT', 10000))
    
    print("\n🎯 QUICK START:")
    print(f"1. Open http://localhost:{port} in your browser to see API status")
    print("2. Open render_app/improved_ada_chart.html to view the enhanced chart")
    print("3. The chart will auto-detect localhost and use the correct API endpoint")
    print("4. Data will update automatically every 30 seconds when auto-refresh is enabled")
    
    try:
        print(f"\n🚀 Starting Flask server on http://localhost:{port}...")
        app.run(host="0.0.0.0", port=port, debug=False)
    except KeyboardInterrupt:
        print("\n⏹️ Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server error: {e}")

if __name__ == "__main__":
    main()
