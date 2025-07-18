# BTC Logger - Enhanced for Historical Data Support
# Updated: 2025-07-10 - Added hybrid data endpoints and improved debugging

from flask_cors import CORS
from process_data import process_csv_to_json
import requests
import csv
import time
import os
from datetime import datetime, UTC
from flask import Flask, jsonify, send_file, send_from_directory, abort
import threading

app = Flask(__name__)
CORS(app)

last_logged = {"timestamp": None}

DATA_FOLDER = "render_app/data"
os.makedirs(DATA_FOLDER, exist_ok=True)

# 🔁 Rotates files every 8 hours (00, 08, 16 UTC)
def get_current_csv_filename():
    now = datetime.now(UTC)
    hour_block = (now.hour // 8) * 8
    block_label = f"{hour_block:02d}"
    date_str = now.strftime("%Y-%m-%d")
    return f"{date_str}_{block_label}.csv"

def fetch_orderbook():
    url = "https://api.exchange.coinbase.com/products/BTC-USD/book?level=2"
    response = requests.get(url)
    data = response.json()

    bids = data.get("bids", [])
    asks = data.get("asks", [])

    best_bid = float(bids[0][0])
    best_ask = float(asks[0][0])
    mid_price = (best_bid + best_ask) / 2
    spread = best_ask - best_bid

    # L20 average spread calculation
    top_bids = [float(b[0]) for b in bids[:20]]
    top_asks = [float(a[0]) for a in asks[:20]]
    if len(top_bids) < 20 or len(top_asks) < 20:
        spread_avg_L20 = spread
        spread_avg_L20_pct = (spread / mid_price) * 100
    else:
        bid_avg = sum(top_bids) / 20
        ask_avg = sum(top_asks) / 20
        spread_avg_L20 = ask_avg - bid_avg
        spread_avg_L20_pct = (spread_avg_L20 / mid_price) * 100

    volume = sum(float(b[1]) for b in bids[:20]) + sum(float(a[1]) for a in asks[:20])
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "asset": "BTC-USD",
        "exchange": "Coinbase",
        "price": mid_price,
        "bid": best_bid,
        "ask": best_ask,
        "spread": spread,
        "volume": volume,
        "spread_avg_L20": spread_avg_L20,
        "spread_avg_L20_pct": spread_avg_L20_pct
    }

def log_data():
    while True:
        start_time = time.time()
        try:
            data = fetch_orderbook()
            filename = os.path.join(DATA_FOLDER, get_current_csv_filename())
            file_exists = os.path.isfile(filename)

            with open(filename, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=data.keys())
                if not file_exists:
                    writer.writeheader()
                writer.writerow(data)

            last_logged["timestamp"] = data["timestamp"]
            print(f"[{data['timestamp']}] ✅ Logged to {filename}")

            # Run comprehensive JSON generation with full historical context
            process_csv_to_json()

        except Exception as e:
            print("🚨 Error in logger loop:", str(e))

        elapsed = time.time() - start_time
        sleep_time = max(0, 1.0 - elapsed)
        time.sleep(sleep_time)

# ---- Flask Routes ----

@app.route("/")
def home():
    return {
        "status": "✅ BTC Logger is running",
        "last_log_time": last_logged["timestamp"],
        "description": "TradingView-style BTC-USD data with hybrid loading system",
        "endpoints": {
            "csv_data": [
                "/data.csv - Current CSV file",
                "/csv-list - List all CSV files",
                "/csv/<filename> - Download specific CSV"
            ],
            "json_data": [
                "/json/output_<YYYY-MM-DD>.json - Daily JSON data",
                "/output-latest.json - Latest daily JSON"
            ],
            "hybrid_chart_data": [
                "/recent.json - Last 24 hours (fast loading, updated every second)",
                "/historical.json - Complete dataset (full history, updated hourly)",
                "/metadata.json - Dataset metadata",
                "/index.json - Data source index"
            ],
            "filtered_data": [
                "/chart-data?limit=1000 - Limited data points",
                "/chart-data?start_date=2025-01-01 - Date filtered data"
            ]
        },
        "chart_integration": {
            "recommended_approach": "Hybrid loading for TradingView-style performance",
            "fast_startup": "Load /recent.json first (instant chart display)",
            "full_historical": "Load /historical.json for complete data",
            "benefits": [
                "Fast initial chart load (24h recent data)",
                "Full historical data available",
                "No chart resets",
                "Scalable performance",
                "Professional trading platform experience"
            ]
        }
    }

@app.route("/data.csv")
def get_current_csv():
    filename = os.path.join(DATA_FOLDER, get_current_csv_filename())
    if os.path.exists(filename):
        return send_file(filename, as_attachment=False)
    else:
        return "No data file available", 404

@app.route("/csv-list")
def list_csvs():
    try:
        files = sorted(os.listdir(DATA_FOLDER))
        return jsonify({"available_csvs": files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/csv/<filename>")
def download_csv(filename):
    try:
        return send_from_directory(DATA_FOLDER, filename)
    except FileNotFoundError:
        abort(404)

@app.route("/json/output_<date>.json")
def serve_json_file(date):
    file_path = os.path.join(DATA_FOLDER, f"output_{date}.json")
    if os.path.exists(file_path):
        return send_file(file_path, mimetype='application/json')
    else:
        return "JSON file not found", 404

@app.route("/output-latest.json")
def serve_latest_output():
    today = datetime.utcnow().date()
    filename = f"output_{today}.json"
    file_path = os.path.join(DATA_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, mimetype='application/json')
    else:
        return "Latest JSON not available", 404

@app.route("/recent.json")
def serve_recent_data():
    """Serve last 24 hours of data for fast chart startup"""
    file_path = os.path.join(DATA_FOLDER, "recent.json")
    if os.path.exists(file_path):
        return send_file(file_path, mimetype='application/json')
    else:
        return jsonify({"error": "Recent data not available"}), 404

@app.route("/historical.json")
def serve_historical_data():
    """Serve complete historical dataset for full TradingView-style charts"""
    file_path = os.path.join(DATA_FOLDER, "historical.json")
    if os.path.exists(file_path):
        return send_file(file_path, mimetype='application/json')
    else:
        return jsonify({"error": "Historical data not available"}), 404

@app.route("/metadata.json")
def serve_metadata():
    """Serve metadata about the dataset"""
    file_path = os.path.join(DATA_FOLDER, "metadata.json")
    if os.path.exists(file_path):
        return send_file(file_path, mimetype='application/json')
    else:
        return jsonify({"error": "Metadata not available"}), 404

@app.route("/index.json")
def serve_index():
    """Serve index of available data files"""
    file_path = os.path.join(DATA_FOLDER, "index.json")
    if os.path.exists(file_path):
        return send_file(file_path, mimetype='application/json')
    else:
        return jsonify({"error": "Index not available"}), 404

@app.route("/chart-data")
def serve_chart_data():
    """Serve optimized data for charting with query parameters"""
    from flask import request
    
    # Check if historical data exists
    historical_path = os.path.join(DATA_FOLDER, "historical.json")
    if not os.path.exists(historical_path):
        return jsonify({"error": "Historical data not available"}), 404
    
    # Get query parameters
    limit = request.args.get('limit', type=int)  # Limit number of records
    start_date = request.args.get('start_date')  # Start date filter
    end_date = request.args.get('end_date')      # End date filter
    
    try:
        import pandas as pd
        df = pd.read_json(historical_path)
        
        # Apply date filters if provided
        if start_date:
            df = df[df['time'] >= start_date]
        if end_date:
            df = df[df['time'] <= end_date]
        
        # Apply limit if provided
        if limit:
            df = df.tail(limit)
        
        # Convert back to JSON
        result = df.to_dict('records')
        
        return jsonify({
            "data": result,
            "count": len(result),
            "filtered": bool(start_date or end_date or limit)
        })
        
    except Exception as e:
        return jsonify({"error": f"Error processing chart data: {str(e)}"}), 500

@app.route("/debug-status")
def debug_status():
    """Debug endpoint to check system status and file timestamps - UPDATED 2025-07-10"""
    try:
        import glob
        status = {
            "timestamp": datetime.utcnow().isoformat(),
            "data_folder": DATA_FOLDER,
            "files": {}
        }
        
        # Check file existence and timestamps
        files_to_check = ["recent.json", "historical.json", "metadata.json", "index.json"]
        
        for filename in files_to_check:
            file_path = os.path.join(DATA_FOLDER, filename)
            if os.path.exists(file_path):
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                age_hours = (datetime.utcnow() - file_time).total_seconds() / 3600
                file_size = os.path.getsize(file_path)
                
                status["files"][filename] = {
                    "exists": True,
                    "last_modified": file_time.isoformat(),
                    "age_hours": round(age_hours, 2),
                    "size_bytes": file_size
                }
            else:
                status["files"][filename] = {"exists": False}
        
        # Check CSV files
        csv_files = glob.glob(os.path.join(DATA_FOLDER, "*.csv"))
        status["csv_files"] = []
        for csv_file in sorted(csv_files):
            file_time = datetime.fromtimestamp(os.path.getmtime(csv_file))
            file_size = os.path.getsize(csv_file)
            status["csv_files"].append({
                "name": os.path.basename(csv_file),
                "last_modified": file_time.isoformat(),
                "size_bytes": file_size
            })
        
        return jsonify(status)
        
    except Exception as e:
        return jsonify({"error": f"Debug status error: {str(e)}"}), 500

# ---- App Runner ----

def run_app():
    app.run(host="0.0.0.0", port=10000)

# Start logger and web server
if __name__ == "__main__":
    threading.Thread(target=log_data, daemon=True).start()
    run_app()
