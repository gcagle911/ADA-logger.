#!/usr/bin/env python3

from flask import Flask, jsonify, send_file, send_from_directory, abort
from flask_cors import CORS
import os
import threading
import time
from datetime import datetime, UTC

from config import get_available_cryptos, get_crypto_config, DEFAULT_CRYPTO
from multi_crypto_logger import CryptoLogger

# Registry of running loggers per symbol
symbol_to_logger = {}

app = Flask(__name__)
CORS(app)


def start_logger_for_symbol(crypto_symbol: str) -> CryptoLogger:
    crypto_symbol = crypto_symbol.upper()
    logger = CryptoLogger(crypto_symbol)

    # Ensure initial JSON exists (try to hydrate from GCS first if enabled)
    recent_file = os.path.join(logger.data_folder, "recent.json")
    historical_file = os.path.join(logger.data_folder, "historical.json")

    try:
        import gcs_utils  # type: ignore
        sync_on_start = os.environ.get("GCS_SYNC_ON_START", "true").lower() == "true"
        if gcs_utils.is_gcs_enabled() and sync_on_start:
            # Hydrate JSONs from GCS-first
            gcs_utils.download_if_exists(recent_file, recent_file)
            gcs_utils.download_if_exists(historical_file, historical_file)
            # Hydrate current CSV for continuity
            asset = os.path.basename(logger.data_folder)
            current_csv = os.path.join(logger.data_folder, logger.get_current_csv_filename())
            csv_blob = os.path.join("csv", asset, logger.get_current_csv_filename())
            gcs_utils.download_if_exists(csv_blob, current_csv)
    except Exception:
        pass

    if not os.path.exists(recent_file):
        print(f"🔄 Creating initial recent.json for {crypto_symbol}")
        logger.process_recent_json()
    if not os.path.exists(historical_file):
        print(f"🔄 Creating initial historical.json for {crypto_symbol}")
        logger.process_historical_json()

    # Start continuous logging with timed JSON generation
    t = threading.Thread(target=logger.log_data_continuous, daemon=True)
    t.start()
    print(f"✅ Started {crypto_symbol} logger thread with timed JSON updates")

    return logger


def ensure_logger(symbol: str) -> CryptoLogger:
    symbol = symbol.upper()
    if symbol not in symbol_to_logger:
        # Only start if symbol is configured
        available = get_available_cryptos()
        if symbol not in available:
            raise KeyError(f"Unknown cryptocurrency: {symbol}")
        symbol_to_logger[symbol] = start_logger_for_symbol(symbol)
    return symbol_to_logger[symbol]


@app.route("/")
def home():
    available = get_available_cryptos()
    base = {
        "status": "✅ Multi-Asset Crypto Logger is running",
        "timestamp": datetime.now(UTC).isoformat(),
        "cryptos": available,
        "endpoints_per_crypto": {
            "status": "/<SYMBOL>/status",
            "csv_data": [
                "/<SYMBOL>/data.csv - Current CSV file",
                "/<SYMBOL>/csv-list - List all CSV files",
                "/<SYMBOL>/csv/<filename> - Download specific CSV",
            ],
            "json_data": [
                "/<SYMBOL>/recent.json - Last 24h (updated 1m)",
                "/<SYMBOL>/historical.json - Full history (updated hourly)",
                "/<SYMBOL>/metadata.json",
                "/<SYMBOL>/index.json",
            ],
        },
    }
    return base


@app.route("/<symbol>/status")
def status(symbol):
    try:
        logger = ensure_logger(symbol)
        config = get_crypto_config(symbol)
        return {
            "crypto": symbol.upper(),
            "pair": config["pair"],
            "exchange": config["exchange"],
            "status": "running",
            "last_logged": logger.last_logged["timestamp"],
            "data_folder": logger.data_folder,
        }
    except KeyError:
        return jsonify({"error": f"Unknown cryptocurrency: {symbol}"}), 404


@app.route("/<symbol>/data.csv")
def get_current_csv(symbol):
    try:
        logger = ensure_logger(symbol)
        filename = os.path.join(logger.data_folder, logger.get_current_csv_filename())
        if os.path.exists(filename):
            return send_file(filename, as_attachment=False)
        else:
            return "No data file available", 404
    except KeyError:
        return jsonify({"error": f"Unknown cryptocurrency: {symbol}"}), 404


@app.route("/<symbol>/csv-list")
def list_csvs(symbol):
    try:
        logger = ensure_logger(symbol)
        files = sorted(os.listdir(logger.data_folder))
        csv_files = [f for f in files if f.endswith('.csv')]
        return jsonify({"available_csvs": csv_files})
    except KeyError:
        return jsonify({"error": f"Unknown cryptocurrency: {symbol}"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/<symbol>/csv/<filename>")
def download_csv(symbol, filename):
    try:
        logger = ensure_logger(symbol)
        return send_from_directory(logger.data_folder, filename)
    except KeyError:
        return jsonify({"error": f"Unknown cryptocurrency: {symbol}"}), 404
    except FileNotFoundError:
        abort(404)


@app.route("/<symbol>/recent.json")
def serve_recent_data(symbol):
    try:
        logger = ensure_logger(symbol)
        file_path = os.path.join(logger.data_folder, "recent.json")
        abs_path = os.path.abspath(file_path)
        if os.path.exists(abs_path):
            return send_file(abs_path, mimetype='application/json')
        else:
            return jsonify({"error": f"Recent data not available at {abs_path}"}), 404
    except KeyError:
        return jsonify({"error": f"Unknown cryptocurrency: {symbol}"}), 404


@app.route("/<symbol>/historical.json")
def serve_historical_data(symbol):
    try:
        logger = ensure_logger(symbol)
        file_path = os.path.join(logger.data_folder, "historical.json")
        abs_path = os.path.abspath(file_path)
        if os.path.exists(abs_path):
            return send_file(abs_path, mimetype='application/json')
        else:
            return jsonify({"error": f"Historical data not available at {abs_path}"}), 404
    except KeyError:
        return jsonify({"error": f"Unknown cryptocurrency: {symbol}"}), 404


@app.route("/<symbol>/metadata.json")
def serve_metadata(symbol):
    try:
        logger = ensure_logger(symbol)
        file_path = os.path.join(logger.data_folder, "metadata.json")
        if os.path.exists(file_path):
            return send_file(file_path, mimetype='application/json')
        else:
            return jsonify({"error": "Metadata not available"}), 404
    except KeyError:
        return jsonify({"error": f"Unknown cryptocurrency: {symbol}"}), 404


@app.route("/<symbol>/index.json")
def serve_index(symbol):
    try:
        logger = ensure_logger(symbol)
        file_path = os.path.join(logger.data_folder, "index.json")
        if os.path.exists(file_path):
            return send_file(file_path, mimetype='application/json')
        else:
            return jsonify({"error": "Index not available"}), 404
    except KeyError:
        return jsonify({"error": f"Unknown cryptocurrency: {symbol}"}), 404


# Backwards-compatibility shortcuts for default crypto at root (e.g., ADA)
@app.route("/recent.json")
def serve_recent_default():
    return serve_recent_data(DEFAULT_CRYPTO)


@app.route("/historical.json")
def serve_historical_default():
    return serve_historical_data(DEFAULT_CRYPTO)


@app.route("/metadata.json")
def serve_metadata_default():
    return serve_metadata(DEFAULT_CRYPTO)


@app.route("/index.json")
def serve_index_default():
    return serve_index(DEFAULT_CRYPTO)


@app.route("/status")
def all_status():
    statuses = {}
    for symbol in get_available_cryptos():
        try:
            logger = ensure_logger(symbol)
            statuses[symbol] = {
                "pair": get_crypto_config(symbol)["pair"],
                "status": "running",
                "last_logged": logger.last_logged["timestamp"],
                "data_folder": logger.data_folder,
            }
        except Exception as e:
            statuses[symbol] = {"status": f"error: {e}"}
    return jsonify(statuses)


@app.route("/gcs-self-test")
def gcs_self_test():
    """Attempt to upload a small test file to GCS and report the result."""
    try:
        import gcs_utils  # type: ignore
        if not gcs_utils.is_gcs_enabled():
            return jsonify({
                "ok": False,
                "error": "GCS not enabled (missing GCS_BUCKET or library)",
            }), 400

        bucket = os.environ.get("GCS_BUCKET", "")
        test_local_dir = os.path.join("render_app", "data")
        os.makedirs(test_local_dir, exist_ok=True)
        test_local_path = os.path.join(test_local_dir, "gcs-self-test.txt")
        with open(test_local_path, "w") as f:
            f.write(f"self-test at {datetime.now(UTC).isoformat()}\n")

        test_blob_path = os.path.join("render_app", "data", "gcs-self-test.txt")
        uploaded = gcs_utils.upload_to_gcs(test_local_path, test_blob_path, content_type="text/plain")

        return jsonify({
            "ok": uploaded,
            "bucket": bucket,
            "blob_path": test_blob_path.replace("\\", "/"),
            "gs_url": f"gs://{bucket}/{test_blob_path.replace('\\', '/')}"
        }), (200 if uploaded else 500)
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


def run_app():
    # Start all configured cryptos
    for symbol in get_available_cryptos():
        try:
            ensure_logger(symbol)
        except Exception as e:
            print(f"❌ Failed to start logger for {symbol}: {e}")

    # Run single Flask app
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 Starting multi-asset server on port {port} for: {', '.join(get_available_cryptos())}")
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    run_app()