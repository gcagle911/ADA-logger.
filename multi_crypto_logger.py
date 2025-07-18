# Multi-Cryptocurrency Logger - Enhanced for Multiple Assets
# Updated: 2025-07-18 - Supports multiple cryptocurrencies simultaneously

from flask_cors import CORS
from flask import Flask, jsonify, send_file, send_from_directory, abort, request
import requests
import csv
import time
import os
import threading
from datetime import datetime, UTC
from config import get_crypto_config, get_available_cryptos, get_crypto_from_port
import sys

class CryptoLogger:
    """Individual cryptocurrency logger"""
    
    def __init__(self, crypto_symbol):
        self.crypto_symbol = crypto_symbol.upper()
        self.config = get_crypto_config(self.crypto_symbol)
        self.last_logged = {"timestamp": None}
        self.data_folder = self.config["data_folder"]
        os.makedirs(self.data_folder, exist_ok=True)
        
    def get_current_csv_filename(self):
        """Generate CSV filename with 8-hour rotation"""
        now = datetime.now(UTC)
        hour_block = (now.hour // 8) * 8
        block_label = f"{hour_block:02d}"
        date_str = now.strftime("%Y-%m-%d")
        return f"{date_str}_{block_label}.csv"
    
    def fetch_orderbook(self):
        """Fetch orderbook data from API"""
        try:
            response = requests.get(self.config["api_url"], timeout=10)
            response.raise_for_status()
            data = response.json()

            bids = data.get("bids", [])
            asks = data.get("asks", [])

            if not bids or not asks:
                raise ValueError("Empty orderbook data")

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
                "timestamp": datetime.now(UTC).isoformat(),
                "asset": self.config["pair"],
                "exchange": self.config["exchange"],
                "price": mid_price,
                "bid": best_bid,
                "ask": best_ask,
                "spread": spread,
                "volume": volume,
                "spread_avg_L20": spread_avg_L20,
                "spread_avg_L20_pct": spread_avg_L20_pct
            }
        except Exception as e:
            print(f"❌ Error fetching {self.crypto_symbol} data: {e}")
            return None

    def log_data_once(self):
        """Log data once"""
        try:
            data = self.fetch_orderbook()
            if data is None:
                return False
                
            filename = os.path.join(self.data_folder, self.get_current_csv_filename())
            file_exists = os.path.isfile(filename)

            with open(filename, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=data.keys())
                if not file_exists:
                    writer.writeheader()
                writer.writerow(data)

            self.last_logged["timestamp"] = data["timestamp"]
            print(f"[{data['timestamp']}] ✅ {self.crypto_symbol} logged to {filename}")
            return True
            
        except Exception as e:
            print(f"🚨 Error logging {self.crypto_symbol}: {str(e)}")
            return False

    def log_data_continuous(self):
        """Continuous logging loop"""
        while True:
            start_time = time.time()
            self.log_data_once()
            
            elapsed = time.time() - start_time
            sleep_time = max(0, 1.0 - elapsed)
            time.sleep(sleep_time)

def create_app(crypto_symbol):
    """Create Flask app for a specific cryptocurrency"""
    crypto_symbol = crypto_symbol.upper()
    config = get_crypto_config(crypto_symbol)
    
    app = Flask(__name__)
    CORS(app)
    
    logger = CryptoLogger(crypto_symbol)
    
    @app.route("/")
    def home():
        return {
            "status": f"✅ {crypto_symbol} Logger is running",
            "crypto": crypto_symbol,
            "pair": config["pair"],
            "last_log_time": logger.last_logged["timestamp"],
            "description": f"TradingView-style {config['pair']} data with hybrid loading system",
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
            "multi_crypto_info": {
                "available_cryptos": get_available_cryptos(),
                "ports": {symbol: get_crypto_config(symbol)["port"] for symbol in get_available_cryptos()},
                "note": "Each cryptocurrency runs on its own port"
            }
        }

    @app.route("/data.csv")
    def get_current_csv():
        filename = os.path.join(logger.data_folder, logger.get_current_csv_filename())
        if os.path.exists(filename):
            return send_file(filename, as_attachment=False)
        else:
            return "No data file available", 404

    @app.route("/csv-list")
    def list_csvs():
        try:
            files = sorted(os.listdir(logger.data_folder))
            csv_files = [f for f in files if f.endswith('.csv')]
            return jsonify({"available_csvs": csv_files})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/csv/<filename>")
    def download_csv(filename):
        try:
            return send_from_directory(logger.data_folder, filename)
        except FileNotFoundError:
            abort(404)
    
    @app.route("/status")
    def status():
        return {
            "crypto": crypto_symbol,
            "pair": config["pair"],
            "status": "running", 
            "last_logged": logger.last_logged["timestamp"],
            "data_folder": logger.data_folder,
            "port": config["port"]
        }
    
    # Store logger in app for access by background thread
    app.crypto_logger = logger
    return app

def run_crypto_server(crypto_symbol, port=None):
    """Run server for a specific cryptocurrency"""
    crypto_symbol = crypto_symbol.upper()
    config = get_crypto_config(crypto_symbol)
    
    if port is None:
        port = config["port"]
    
    app = create_app(crypto_symbol)
    logger = app.crypto_logger
    
    # Start logging thread
    logging_thread = threading.Thread(target=logger.log_data_continuous, daemon=True)
    logging_thread.start()
    print(f"✅ Started {crypto_symbol} logger thread")
    
    print(f"🚀 Starting {crypto_symbol} server on port {port}")
    try:
        app.run(host="0.0.0.0", port=port, debug=False)
    except Exception as e:
        print(f"❌ Error running {crypto_symbol} server: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        crypto = sys.argv[1].upper()
        if crypto in get_available_cryptos():
            run_crypto_server(crypto)
        else:
            print(f"❌ Unknown cryptocurrency: {crypto}")
            print(f"Available: {', '.join(get_available_cryptos())}")
    else:
        print("Usage: python multi_crypto_logger.py <CRYPTO>")
        print(f"Available cryptocurrencies: {', '.join(get_available_cryptos())}")
        print("\nExample: python multi_crypto_logger.py ADA")