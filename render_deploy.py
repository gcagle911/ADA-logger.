#!/usr/bin/env python3
"""
Render Deployment Script for Multi-Crypto Logger
Updated: 2025-07-30 23:40 UTC - L5 data fixes applied
"""

import os
import sys
import signal
import threading
import time
from multiprocessing import Process

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import get_crypto_config, get_available_cryptos
from multi_crypto_logger import create_app, CryptoLogger


def run_single_crypto(crypto_symbol, port=None):
    """Run a single cryptocurrency logger"""
    try:
        config = get_crypto_config(crypto_symbol)
        if port is None:
            port = int(os.environ.get('PORT', config['port']))
        
        print(f"🚀 Starting {crypto_symbol} logger on port {port}")
        
        # Create Flask app and start logger
        app = create_app(crypto_symbol)
        logger = app.crypto_logger
        
        # Start logging thread
        logging_thread = threading.Thread(target=logger.log_data_continuous, daemon=True)
        logging_thread.start()
        print(f"✅ Started {crypto_symbol} logger thread")
        
        # Run the Flask app
        app.run(host="0.0.0.0", port=port, debug=False)
        
    except Exception as e:
        print(f"❌ Error running {crypto_symbol}: {e}")
        sys.exit(1)


def run_multiple_cryptos(crypto_symbols):
    """Run multiple cryptocurrency loggers (for advanced deployment)"""
    processes = []
    
    try:
        for i, symbol in enumerate(crypto_symbols):
            config = get_crypto_config(symbol)
            port = config['port']
            
            print(f"🚀 Starting {symbol} process on port {port}")
            process = Process(target=run_single_crypto, args=(symbol, port))
            process.start()
            processes.append(process)
            
        # Wait for all processes
        for process in processes:
            process.join()
            
    except KeyboardInterrupt:
        print("🛑 Shutting down all crypto loggers...")
        for process in processes:
            process.terminate()
        sys.exit(0)


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully"""
    print("\n🛑 Received shutdown signal. Cleaning up...")
    sys.exit(0)


def main():
    """Main entry point for Render deployment"""
    # Setup signal handling
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("🌟 Starting Render Crypto Logger Deployment")
    print(f"📂 Working directory: {os.getcwd()}")
    print(f"🐍 Python version: {sys.version}")
    
    # Check for environment variables
    single_crypto = os.environ.get('CRYPTO_SYMBOL', '').upper().strip()
    multiple_cryptos = os.environ.get('CRYPTO_SYMBOLS', '').upper().strip()
    
    if single_crypto:
        if single_crypto in get_available_cryptos():
            print(f"🎯 Single crypto mode: {single_crypto}")
            run_single_crypto(single_crypto)
        else:
            print(f"❌ Unknown cryptocurrency: {single_crypto}")
            print(f"Available: {', '.join(get_available_cryptos())}")
            sys.exit(1)
            
    elif multiple_cryptos:
        crypto_list = [c.strip() for c in multiple_cryptos.split(',') if c.strip()]
        valid_cryptos = [c for c in crypto_list if c in get_available_cryptos()]
        
        if valid_cryptos:
            print(f"🎯 Multi-crypto mode: {', '.join(valid_cryptos)}")
            run_multiple_cryptos(valid_cryptos)
        else:
            print(f"❌ No valid cryptocurrencies found in: {multiple_cryptos}")
            print(f"Available: {', '.join(get_available_cryptos())}")
            sys.exit(1)
    else:
        # Default to ADA if no environment variables set
        print("🎯 No crypto specified, defaulting to ADA")
        print("💡 Set CRYPTO_SYMBOL=<symbol> or CRYPTO_SYMBOLS=<list> for different cryptos")
        run_single_crypto('ADA')


if __name__ == "__main__":
    main()