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
        self.last_json_update = {"recent": time.time(), "historical": time.time()}  # Track last JSON updates
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

            # L5 average spread calculation (top 5 orderbook levels)
            top_bids = [float(b[0]) for b in bids[:5]]
            top_asks = [float(a[0]) for a in asks[:5]]
            if len(top_bids) < 5 or len(top_asks) < 5:
                spread_avg_L5 = spread
                spread_avg_L5_pct = (spread / mid_price) * 100
            else:
                bid_avg = sum(top_bids) / 5
                ask_avg = sum(top_asks) / 5
                spread_avg_L5 = ask_avg - bid_avg
                spread_avg_L5_pct = (spread_avg_L5 / mid_price) * 100

            volume = sum(float(b[1]) for b in bids[:5]) + sum(float(a[1]) for a in asks[:5])
            
            return {
                "timestamp": datetime.now(UTC).isoformat(),
                "asset": self.config["pair"],
                "exchange": self.config["exchange"],
                "price": mid_price,
                "bid": best_bid,
                "ask": best_ask,
                "spread": spread,
                "volume": volume,
                "spread_avg_L5": spread_avg_L5,
                "spread_avg_L5_pct": spread_avg_L5_pct
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
            
            # NO automatic JSON processing - use separate timer thread
            return True
            
        except Exception as e:
            print(f"🚨 Error logging {self.crypto_symbol}: {str(e)}")
            return False

    def check_and_process_json(self):
        """Check if JSON files need updating based on proper intervals"""
        current_time = time.time()
        
        # Force generation if files don't exist (for fresh deployments) - ONLY ONCE
        recent_file = os.path.join(self.data_folder, "recent.json")
        historical_file = os.path.join(self.data_folder, "historical.json")
        
        if not os.path.exists(recent_file):
            print(f"🔄 Force generating missing recent.json for {self.crypto_symbol}")
            self.process_recent_json()
            self.last_json_update["recent"] = current_time
            return  # Exit early to avoid double processing
            
        if not os.path.exists(historical_file):
            print(f"🔄 Force generating missing historical.json for {self.crypto_symbol}")
            self.process_historical_json()
            self.last_json_update["historical"] = current_time
            return  # Exit early to avoid double processing
        
        # Recent JSON: Update every 60 seconds (1 minute) - STRICT TIMING
        if current_time - self.last_json_update["recent"] >= 60:
            print(f"📊 Updating recent.json for {self.crypto_symbol} (60 second interval)")
            self.process_recent_json()
            self.last_json_update["recent"] = current_time
            
        # Historical JSON: Update every 3600 seconds (1 hour) - STRICT TIMING
        if current_time - self.last_json_update["historical"] >= 3600:
            print(f"🏛️ Updating historical.json for {self.crypto_symbol} (1 hour interval)")
            self.process_historical_json()
            self.last_json_update["historical"] = current_time

    def process_recent_json(self):
        """Generate recent.json file"""
        try:
            # Import here to avoid circular imports
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            from process_data import process_csv_to_json
            import process_data
            
            # Temporarily set DATA_FOLDER for this crypto's processing
            original_folder = getattr(process_data, 'DATA_FOLDER', None)
            process_data.DATA_FOLDER = self.data_folder
            
            # Process only recent data
            process_csv_to_json()
            print(f"📊 Updated recent.json for {self.crypto_symbol}")
            
            # Restore original folder
            if original_folder:
                process_data.DATA_FOLDER = original_folder
                
        except Exception as e:
            print(f"❌ Error updating recent JSON for {self.crypto_symbol}: {e}")

    def process_historical_json(self):
        """Generate historical.json file"""
        try:
            # Import here to avoid circular imports
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            from process_data import process_csv_to_json
            import process_data
            
            # Temporarily set DATA_FOLDER for this crypto's processing
            original_folder = getattr(process_data, 'DATA_FOLDER', None)
            process_data.DATA_FOLDER = self.data_folder
            
            # Process full historical data  
            process_csv_to_json()
            print(f"🏛️ Updated historical.json for {self.crypto_symbol}")
            
            # Restore original folder
            if original_folder:
                process_data.DATA_FOLDER = original_folder
                
        except Exception as e:
            print(f"❌ Error updating historical JSON for {self.crypto_symbol}: {e}")

    def cleanup_old_csv_files(self, keep_days=7):
        """Remove CSV files older than keep_days to prevent disk space issues"""
        try:
            import glob
            from pathlib import Path
            
            # Get all CSV files in the data folder
            csv_pattern = os.path.join(self.data_folder, "*.csv")
            csv_files = glob.glob(csv_pattern)
            
            # Current time for comparison
            now = datetime.now(UTC)
            cutoff_time = now - timedelta(days=keep_days)
            
            deleted_count = 0
            for csv_file in csv_files:
                try:
                    # Get file modification time
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(csv_file), tz=UTC)
                    
                    if file_mtime < cutoff_time:
                        os.remove(csv_file)
                        deleted_count += 1
                        print(f"🗑️ Deleted old CSV: {os.path.basename(csv_file)}")
                        
                except Exception as e:
                    print(f"⚠️ Error deleting {csv_file}: {e}")
            
            if deleted_count > 0:
                print(f"🧹 Cleanup complete: removed {deleted_count} old CSV files for {self.crypto_symbol}")
            
        except Exception as e:
            print(f"❌ Error during CSV cleanup for {self.crypto_symbol}: {e}")

    def log_data_continuous(self):
        """Continuous logging loop with proper JSON timing"""
        json_counter = 0  # Simple counter for JSON generation
        
        while True:
            start_time = time.time()
            self.log_data_once()
            
            json_counter += 1
            
            # Update recent.json every 5 minutes (300 seconds)
            if json_counter % 300 == 0:
                print(f"📊 5-minute interval - updating recent.json for {self.crypto_symbol}")
                try:
                    self.process_recent_json()
                except Exception as e:
                    print(f"❌ Error updating recent.json: {e}")
            
            # Update historical.json every 1 hour (3600 seconds) 
            if json_counter % 3600 == 0:
                print(f"🏛️ 1-hour interval - updating historical.json for {self.crypto_symbol}")
                try:
                    self.process_historical_json()
                    # Also cleanup old CSV files to prevent disk space issues
                    self.cleanup_old_csv_files()
                except Exception as e:
                    print(f"❌ Error updating historical.json: {e}")
                json_counter = 0  # Reset to prevent overflow
            
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
                    "/recent.json - Last 24 hours (fast loading, updated every minute)",
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
    
    # JSON Data Endpoints for plotting
    @app.route("/recent.json")
    def serve_recent_data():
        """Serve last 24 hours of data for fast chart startup"""
        file_path = os.path.join(logger.data_folder, "recent.json")
        abs_path = os.path.abspath(file_path)
        print(f"🔍 Looking for recent.json at: {abs_path}")
        print(f"✅ File exists: {os.path.exists(abs_path)}")
        if os.path.exists(abs_path):
            return send_file(abs_path, mimetype='application/json')
        else:
            return jsonify({"error": f"Recent data not available at {abs_path}"}), 404

    @app.route("/historical.json")
    def serve_historical_data():
        """Serve complete historical dataset for full TradingView-style charts"""
        file_path = os.path.join(logger.data_folder, "historical.json")
        abs_path = os.path.abspath(file_path)
        print(f"🔍 Looking for historical.json at: {abs_path}")
        print(f"📂 Current working directory: {os.getcwd()}")
        print(f"📁 Data folder: {logger.data_folder}")
        print(f"✅ File exists: {os.path.exists(abs_path)}")
        if os.path.exists(abs_path):
            return send_file(abs_path, mimetype='application/json')
        else:
            return jsonify({"error": f"Historical data not available at {abs_path}"}), 404

    @app.route("/metadata.json")
    def serve_metadata():
        """Serve metadata about the dataset"""
        file_path = os.path.join(logger.data_folder, "metadata.json")
        if os.path.exists(file_path):
            return send_file(file_path, mimetype='application/json')
        else:
            return jsonify({"error": "Metadata not available"}), 404

    @app.route("/index.json")
    def serve_index():
        """Serve index of available data files"""
        file_path = os.path.join(logger.data_folder, "index.json")
        if os.path.exists(file_path):
            return send_file(file_path, mimetype='application/json')
        else:
            return jsonify({"error": "Index not available"}), 404

    @app.route("/generate-json")
    def generate_json_now():
        """Manually trigger JSON generation and reset timing (for fresh deployments)"""
        try:
            print(f"🔧 Manual JSON generation triggered for {crypto_symbol}")
            
            # Reset timing to ensure fresh generation
            current_time = time.time()
            logger.last_json_update = {"recent": 0, "historical": 0}
            
            # Force generate both files
            logger.process_recent_json()
            logger.process_historical_json()
            
            # Reset timing properly for future automatic updates
            logger.last_json_update = {"recent": current_time, "historical": current_time}
            
            return jsonify({
                "status": "✅ JSON files generated successfully with L5 data",
                "recent_json": "/recent.json",
                "historical_json": "/historical.json", 
                "crypto": crypto_symbol,
                "timestamp": datetime.now(UTC).isoformat(),
                "timing": {
                    "recent_json": "Updates automatically every 5 minutes (300 seconds)",
                    "historical_json": "Updates automatically every 1 hour (3600 seconds)",
                    "csv_rotation": "Every 8 hours with 7-day cleanup"
                },
                "note": "Manual generation complete. Automatic updates use counter-based timing."
            })
        except Exception as e:
            import traceback
            return jsonify({
                "error": f"❌ Error generating JSON: {e}", 
                "traceback": traceback.format_exc(),
                "crypto": crypto_symbol
            }), 500
    
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
    
    # Generate initial JSON files if they don't exist
    recent_file = os.path.join(logger.data_folder, "recent.json")
    historical_file = os.path.join(logger.data_folder, "historical.json")
    
    if not os.path.exists(recent_file):
        print(f"🔄 Creating initial recent.json for {crypto_symbol}")
        logger.process_recent_json()
        
    if not os.path.exists(historical_file):
        print(f"🔄 Creating initial historical.json for {crypto_symbol}")
        logger.process_historical_json()
    
    # Start logging thread
    logging_thread = threading.Thread(target=logger.log_data_continuous, daemon=True)
    logging_thread.start()
    print(f"✅ Started {crypto_symbol} logger thread with timed JSON updates")
    
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