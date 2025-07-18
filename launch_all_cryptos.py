#!/usr/bin/env python3
"""
Multi-Cryptocurrency Logger Launcher
====================================

This script launches multiple cryptocurrency loggers simultaneously,
each running on its own port for parallel data collection.
"""

import os
import sys
import time
import signal
import subprocess
from concurrent.futures import ThreadPoolExecutor
from config import get_available_cryptos, get_crypto_config

class MultiCryptoLauncher:
    def __init__(self):
        self.processes = {}
        self.running = True
        
    def launch_crypto_logger(self, crypto_symbol):
        """Launch a single cryptocurrency logger"""
        try:
            config = get_crypto_config(crypto_symbol)
            port = config["port"]
            
            print(f"🚀 Starting {crypto_symbol} logger on port {port}...")
            
            # Start the process
            process = subprocess.Popen([
                sys.executable, "multi_crypto_logger.py", crypto_symbol
            ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            
            self.processes[crypto_symbol] = process
            
            # Monitor the process output
            while self.running and process.poll() is None:
                output = process.stdout.readline()
                if output:
                    print(f"[{crypto_symbol}] {output.strip()}")
                time.sleep(0.1)
                    
        except Exception as e:
            print(f"❌ Error launching {crypto_symbol}: {e}")
    
    def launch_all(self, cryptos=None):
        """Launch all cryptocurrency loggers"""
        if cryptos is None:
            cryptos = get_available_cryptos()
        
        print("🌟 Multi-Cryptocurrency Logger")
        print("=" * 50)
        print(f"📊 Launching loggers for: {', '.join(cryptos)}")
        print("=" * 50)
        
        # Display port assignments
        for crypto in cryptos:
            config = get_crypto_config(crypto)
            print(f"• {crypto}: http://localhost:{config['port']} -> {config['pair']}")
        
        print("\n🚀 Starting all loggers...")
        
        # Launch all in parallel
        with ThreadPoolExecutor(max_workers=len(cryptos)) as executor:
            futures = []
            for crypto in cryptos:
                future = executor.submit(self.launch_crypto_logger, crypto)
                futures.append(future)
            
            try:
                # Wait for all to complete (or until interrupted)
                for future in futures:
                    future.result()
            except KeyboardInterrupt:
                self.shutdown()
    
    def shutdown(self):
        """Shutdown all processes"""
        print("\n🛑 Shutting down all cryptocurrency loggers...")
        self.running = False
        
        for crypto, process in self.processes.items():
            if process.poll() is None:
                print(f"⏹️ Stopping {crypto} logger...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print(f"⚠️ Force killing {crypto} logger...")
                    process.kill()
        
        print("✅ All loggers stopped")
    
    def status(self):
        """Check status of all processes"""
        print("\n📊 Cryptocurrency Logger Status:")
        print("-" * 40)
        for crypto, process in self.processes.items():
            if process.poll() is None:
                config = get_crypto_config(crypto)
                print(f"✅ {crypto}: Running on port {config['port']}")
            else:
                print(f"❌ {crypto}: Stopped")

def launch_specific_cryptos():
    """Launch specific cryptocurrencies based on command line arguments"""
    if len(sys.argv) > 1:
        cryptos = [arg.upper() for arg in sys.argv[1:]]
        # Validate cryptos
        available = get_available_cryptos()
        invalid = [c for c in cryptos if c not in available]
        if invalid:
            print(f"❌ Unknown cryptocurrencies: {', '.join(invalid)}")
            print(f"Available: {', '.join(available)}")
            return
        return cryptos
    return None

def show_usage():
    """Show usage information"""
    available = get_available_cryptos()
    print("🌟 Multi-Cryptocurrency Logger Launcher")
    print("=" * 50)
    print("\nUsage:")
    print("  python launch_all_cryptos.py                    # Launch all cryptos")
    print("  python launch_all_cryptos.py ADA BTC ETH        # Launch specific cryptos")
    print("  python launch_all_cryptos.py --help             # Show this help")
    print("\nAvailable cryptocurrencies:")
    for crypto in available:
        config = get_crypto_config(crypto)
        print(f"  • {crypto}: {config['pair']} (port {config['port']})")
    
    print("\nEach cryptocurrency will run on its own port:")
    for crypto in available:
        config = get_crypto_config(crypto)
        print(f"  • {crypto}: http://localhost:{config['port']}")
    
    print("\n💡 Tips:")
    print("  • Each crypto logger runs independently")
    print("  • Data is stored in separate folders per crypto")
    print("  • All loggers can run simultaneously")
    print("  • Use Ctrl+C to stop all loggers")

def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h', 'help']:
        show_usage()
        return
    
    launcher = MultiCryptoLauncher()
    
    # Setup signal handler for graceful shutdown
    def signal_handler(signum, frame):
        launcher.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Determine which cryptos to launch
    cryptos = launch_specific_cryptos()
    
    try:
        launcher.launch_all(cryptos)
    except KeyboardInterrupt:
        launcher.shutdown()
    except Exception as e:
        print(f"❌ Error: {e}")
        launcher.shutdown()

if __name__ == "__main__":
    main()