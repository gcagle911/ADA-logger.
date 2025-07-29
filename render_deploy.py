#!/usr/bin/env python3
"""
Render Deployment Script for Multi-Crypto Logger
===============================================

This script is designed to run on Render.com and can be configured via environment variables
to run single or multiple cryptocurrency loggers.

Environment Variables:
- CRYPTO_SYMBOL: Single crypto to run (e.g., "ADA", "BTC", "ETH", "XRP")
- CRYPTO_SYMBOLS: Multiple cryptos comma-separated (e.g., "ADA,BTC,ETH,XRP")
- PORT: Port to run on (default: 10000, Render will set this automatically)

If no environment variables are set, defaults to running ADA on port 10000.
"""

import os
import sys
import signal
import threading
import time
from multiprocessing import Process

# Add current directory to path
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
    """Run multiple cryptocurrency loggers in separate processes"""
    processes = []
    
    def signal_handler(signum, frame):
        print("\n🛑 Shutting down all crypto loggers...")
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
                if process.is_alive():
                    process.kill()
        sys.exit(0)
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start each crypto in a separate process
    for i, crypto_symbol in enumerate(crypto_symbols):
        try:
            config = get_crypto_config(crypto_symbol)
            port = config['port']
            
            # For Render, only the first process should use the PORT env var
            if i == 0:
                port = int(os.environ.get('PORT', port))
            
            print(f"🚀 Starting {crypto_symbol} on port {port}")
            
            process = Process(target=run_single_crypto, args=(crypto_symbol, port))
            process.start()
            processes.append(process)
            
            # Small delay between starts
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ Error starting {crypto_symbol}: {e}")
    
    # Wait for all processes
    try:
        for process in processes:
            process.join()
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)


def main():
    """Main deployment function"""
    print("🌟 Multi-Crypto Logger - Render Deployment")
    print("=" * 50)
    
    # Check environment variables
    single_crypto = os.environ.get('CRYPTO_SYMBOL', '').upper()
    multiple_cryptos = os.environ.get('CRYPTO_SYMBOLS', '')
    port = os.environ.get('PORT')
    
    print(f"Environment: PORT={port}, CRYPTO_SYMBOL={single_crypto}, CRYPTO_SYMBOLS={multiple_cryptos}")
    
    # Validate available cryptos
    available_cryptos = get_available_cryptos()
    print(f"Available cryptocurrencies: {', '.join(available_cryptos)}")
    
    if multiple_cryptos:
        # Run multiple cryptos
        crypto_list = [crypto.strip().upper() for crypto in multiple_cryptos.split(',')]
        crypto_list = [crypto for crypto in crypto_list if crypto in available_cryptos]
        
        if not crypto_list:
            print("❌ No valid cryptocurrencies found in CRYPTO_SYMBOLS")
            sys.exit(1)
        
        print(f"🔄 Running multiple cryptocurrencies: {', '.join(crypto_list)}")
        run_multiple_cryptos(crypto_list)
        
    elif single_crypto and single_crypto in available_cryptos:
        # Run single crypto
        print(f"📊 Running single cryptocurrency: {single_crypto}")
        run_single_crypto(single_crypto)
        
    else:
        # Default to ADA
        default_crypto = 'ADA'
        print(f"🔄 No valid crypto specified, defaulting to {default_crypto}")
        run_single_crypto(default_crypto)


if __name__ == "__main__":
    main()