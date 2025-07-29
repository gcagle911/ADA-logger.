# Multi-Cryptocurrency Logger Guide

## Overview

Your repository now supports logging **multiple cryptocurrencies simultaneously**! Each cryptocurrency runs on its own port and stores data in separate folders, allowing you to collect data from multiple assets without conflicts.

## ✅ What's Been Done

### 1. **Converted BTC → ADA Logger**
- ✅ Changed from Bitcoin to Cardano (ADA) data logging
- ✅ Updated API endpoints to use `ADA-USD` pair
- ✅ Adjusted price ranges for ADA (around $0.85 vs $65,000 for BTC)
- ✅ Fixed all deprecation warnings

### 2. **Created Multi-Crypto Support**
- ✅ **`config.py`**: Central configuration for all cryptocurrencies
- ✅ **`multi_crypto_logger.py`**: Individual crypto logger that can handle any configured crypto
- ✅ **`launch_all_cryptos.py`**: Master launcher to run multiple cryptos simultaneously

## 🚀 Quick Start

### Single Cryptocurrency
```bash
# Run just ADA logger
python3 multi_crypto_logger.py ADA

# Run just BTC logger  
python3 multi_crypto_logger.py BTC

# Run just ETH logger
python3 multi_crypto_logger.py ETH

# Run just XRP logger
python3 multi_crypto_logger.py XRP
```

### Multiple Cryptocurrencies
```bash
# Run ALL configured cryptocurrencies
python3 launch_all_cryptos.py

# Run specific cryptocurrencies
python3 launch_all_cryptos.py ADA BTC ETH XRP

# Get help
python3 launch_all_cryptos.py --help
```

## 📊 Supported Cryptocurrencies

| Symbol | Pair     | Port  | Data Folder            | API Source |
|--------|----------|-------|------------------------|------------|
| ADA    | ADA-USD  | 10000 | `render_app/data/ada`  | Coinbase   |
| BTC    | BTC-USD  | 10001 | `render_app/data/btc`  | Coinbase   |
| ETH    | ETH-USD  | 10002 | `render_app/data/eth`  | Coinbase   |
| SOL    | SOL-USD  | 10003 | `render_app/data/sol`  | Coinbase   |
| DOT    | DOT-USD  | 10004 | `render_app/data/dot`  | Coinbase   |
| XRP    | XRP-USD  | 10005 | `render_app/data/xrp`  | Coinbase   |

## 🌐 API Endpoints

Each cryptocurrency runs on its own port with identical API structure:

### ADA (Port 10000)
- **Status**: http://localhost:10000/
- **Current CSV**: http://localhost:10000/data.csv
- **CSV List**: http://localhost:10000/csv-list
- **Status**: http://localhost:10000/status

### BTC (Port 10001)
- **Status**: http://localhost:10001/
- **Current CSV**: http://localhost:10001/data.csv
- etc...

### ETH (Port 10002)
- **Status**: http://localhost:10002/
- etc...

### XRP (Port 10005)
- **Status**: http://localhost:10005/
- **Current CSV**: http://localhost:10005/data.csv
- **CSV List**: http://localhost:10005/csv-list
- **Status**: http://localhost:10005/status

## 📁 Data Organization

```
render_app/data/
├── ada/                    # ADA data
│   ├── 2025-07-18_08.csv
│   ├── 2025-07-18_16.csv
│   └── ...
├── btc/                    # BTC data  
│   ├── 2025-07-18_08.csv
│   └── ...
├── eth/                    # ETH data
│   └── ...
├── sol/                    # SOL data
│   └── ...
├── dot/                    # DOT data
│   └── ...
└── xrp/                    # XRP data
    └── ...
```

## ⚙️ Configuration

Edit `config.py` to add more cryptocurrencies or modify settings:

```python
CRYPTO_CONFIGS = {
    "NEW_CRYPTO": {
        "pair": "NEW-USD",
        "exchange": "Coinbase", 
        "api_url": "https://api.exchange.coinbase.com/products/NEW-USD/book?level=2",
        "base_price": 1.50,
        "price_change_range": 100,
        "price_change_divisor": 1000,
        "price_increment": 0.001,
        "data_folder": "render_app/data/new_crypto",
        "port": 10005
    }
}
```

## 🔄 Migration from Single to Multi-Crypto

### Option 1: Keep Using Single ADA Logger
Your existing `start_server.py` still works for ADA only:
```bash
python3 start_server.py  # ADA only on port 10000
```

### Option 2: Switch to Multi-Crypto System
Use the new system for more flexibility:
```bash
python3 multi_crypto_logger.py ADA  # ADA only, new system
python3 launch_all_cryptos.py ADA BTC  # Multiple cryptos
```

## 🛠️ How It Works

### Single Crypto Logger (`multi_crypto_logger.py`)
1. **Configurable**: Uses `config.py` for all settings
2. **Independent**: Each crypto runs in its own process/port
3. **Data Separation**: Each crypto stores data in its own folder
4. **Real-time**: Fetches live data from Coinbase every second

### Multi-Crypto Launcher (`launch_all_cryptos.py`)
1. **Parallel Execution**: Runs multiple crypto loggers simultaneously
2. **Process Management**: Handles starting/stopping all loggers
3. **Graceful Shutdown**: Ctrl+C stops all loggers cleanly
4. **Flexible**: Can launch any combination of cryptos

## 🔍 Monitoring

### Check Status of All Running Cryptos
```bash
# Check individual crypto status
curl http://localhost:10000/status  # ADA
curl http://localhost:10001/status  # BTC  
curl http://localhost:10002/status  # ETH
curl http://localhost:10005/status  # XRP
```

### View Real-time Logs
When running `launch_all_cryptos.py`, you'll see logs from all cryptos:
```
[ADA] ✅ ADA logged to render_app/data/ada/2025-07-18_08.csv
[BTC] ✅ BTC logged to render_app/data/btc/2025-07-18_08.csv
[ETH] ✅ ETH logged to render_app/data/eth/2025-07-18_08.csv
[XRP] ✅ XRP logged to render_app/data/xrp/2025-07-18_08.csv
```

## 🎯 Use Cases

### Development/Testing
```bash
# Test just one crypto
python3 multi_crypto_logger.py ADA
```

### Production Data Collection
```bash
# Collect data from multiple cryptos 24/7
python3 launch_all_cryptos.py ADA BTC ETH SOL DOT XRP
```

### Selective Monitoring
```bash
# Monitor just the big ones
python3 launch_all_cryptos.py BTC ETH
```

## 🚨 Troubleshooting

### Port Conflicts
If you get port binding errors:
1. Check what's running: `lsof -i :10000`
2. Kill existing processes: `pkill -f multi_crypto_logger`
3. Or change ports in `config.py`

### Missing Dependencies
```bash
pip3 install --break-system-packages flask flask-cors requests pandas
```

### Data Folder Permissions
```bash
mkdir -p render_app/data/{ada,btc,eth,sol,dot,xrp}
chmod 755 render_app/data/*
```

## 🎉 Benefits of Multi-Crypto System

1. **Parallel Collection**: Collect data from multiple assets simultaneously
2. **Independent Operations**: One crypto failure doesn't affect others
3. **Scalable**: Easy to add new cryptocurrencies
4. **Organized**: Clean data separation by asset
5. **Flexible**: Run any combination of cryptos
6. **Production Ready**: Robust process management
7. **API Consistency**: Same API structure for all cryptos

## 🔧 Next Steps

1. **Start with ADA**: `python3 multi_crypto_logger.py ADA`
2. **Add more cryptos**: `python3 launch_all_cryptos.py ADA BTC ETH XRP`
3. **Customize config**: Edit `config.py` to add your preferred cryptos
4. **Build charts**: Each crypto has the same API endpoints for charting
5. **Monitor & scale**: Add more cryptocurrencies as needed

Your repository is now a **professional-grade multi-cryptocurrency data collection system**! 🚀