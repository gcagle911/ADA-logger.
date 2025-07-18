# Multi-Cryptocurrency Logger Configuration
# Configure which cryptocurrencies to log and their settings

CRYPTO_CONFIGS = {
    "ADA": {
        "pair": "ADA-USD",
        "exchange": "Coinbase",
        "api_url": "https://api.exchange.coinbase.com/products/ADA-USD/book?level=2",
        "base_price": 0.85,  # For sample data generation
        "price_change_range": 200,  # Random price movement range
        "price_change_divisor": 10000,  # Price movement scale
        "price_increment": 0.0001,  # Upward trend increment
        "data_folder": "render_app/data/ada",
        "port": 10000
    },
    "BTC": {
        "pair": "BTC-USD", 
        "exchange": "Coinbase",
        "api_url": "https://api.exchange.coinbase.com/products/BTC-USD/book?level=2",
        "base_price": 65000,
        "price_change_range": 2000,
        "price_change_divisor": 100,
        "price_increment": 0.1,
        "data_folder": "render_app/data/btc",
        "port": 10001
    },
    "ETH": {
        "pair": "ETH-USD",
        "exchange": "Coinbase", 
        "api_url": "https://api.exchange.coinbase.com/products/ETH-USD/book?level=2",
        "base_price": 3500,
        "price_change_range": 400,
        "price_change_divisor": 100,
        "price_increment": 0.05,
        "data_folder": "render_app/data/eth",
        "port": 10002
    },
    "SOL": {
        "pair": "SOL-USD",
        "exchange": "Coinbase",
        "api_url": "https://api.exchange.coinbase.com/products/SOL-USD/book?level=2", 
        "base_price": 140,
        "price_change_range": 500,
        "price_change_divisor": 100,
        "price_increment": 0.02,
        "data_folder": "render_app/data/sol",
        "port": 10003
    },
    "DOT": {
        "pair": "DOT-USD",
        "exchange": "Coinbase",
        "api_url": "https://api.exchange.coinbase.com/products/DOT-USD/book?level=2",
        "base_price": 7.5,
        "price_change_range": 150,
        "price_change_divisor": 1000,
        "price_increment": 0.005,
        "data_folder": "render_app/data/dot",
        "port": 10004
    }
}

# Default configuration (for backward compatibility)
DEFAULT_CRYPTO = "ADA"

# Server settings
DEFAULT_PORT = 10000
LOG_INTERVAL = 1  # seconds
FILE_ROTATION_HOURS = 8  # hours

def get_crypto_config(crypto_symbol):
    """Get configuration for a specific cryptocurrency"""
    return CRYPTO_CONFIGS.get(crypto_symbol.upper(), CRYPTO_CONFIGS[DEFAULT_CRYPTO])

def get_available_cryptos():
    """Get list of available cryptocurrencies"""
    return list(CRYPTO_CONFIGS.keys())

def get_crypto_from_port(port):
    """Get crypto symbol from port number"""
    for symbol, config in CRYPTO_CONFIGS.items():
        if config["port"] == port:
            return symbol
    return DEFAULT_CRYPTO