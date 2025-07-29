# JSON Endpoints Guide for Chart Integration

## 🎯 **Fixed & Ready for Plotting!**

Your repository is now fully configured to provide **both historical and recent JSON endpoints** for seamless chart integration! ✅

## 📍 **JSON File Locations**

### **Individual Crypto Directories (Recommended)**
Each cryptocurrency maintains its own JSON files in dedicated folders:

```
render_app/data/ada/          # ADA data
├── historical.json           # Complete dataset (all time)
├── recent.json              # Last 24 hours
├── metadata.json            # Dataset information
├── index.json               # File index
└── output_2025-MM-DD.json   # Daily snapshots

render_app/data/xrp/          # XRP data
├── historical.json           # Complete dataset (all time)
├── recent.json              # Last 24 hours
├── metadata.json            # Dataset information
├── index.json               # File index
└── output_2025-MM-DD.json   # Daily snapshots

render_app/data/btc/          # BTC data (when running)
render_app/data/eth/          # ETH data (when running)
render_app/data/sol/          # SOL data (when running)
render_app/data/dot/          # DOT data (when running)
```

## 🌐 **API Endpoints for Chart Applications**

### **For Individual Cryptos (Recommended)**

| Crypto | Port | Historical JSON | Recent JSON | Metadata |
|--------|------|----------------|-------------|----------|
| ADA    | 10000| `http://localhost:10000/historical.json` | `http://localhost:10000/recent.json` | `http://localhost:10000/metadata.json` |
| BTC    | 10001| `http://localhost:10001/historical.json` | `http://localhost:10001/recent.json` | `http://localhost:10001/metadata.json` |
| ETH    | 10002| `http://localhost:10002/historical.json` | `http://localhost:10002/recent.json` | `http://localhost:10002/metadata.json` |
| SOL    | 10003| `http://localhost:10003/historical.json` | `http://localhost:10003/recent.json` | `http://localhost:10003/metadata.json` |
| DOT    | 10004| `http://localhost:10004/historical.json` | `http://localhost:10004/recent.json` | `http://localhost:10004/metadata.json` |
| XRP    | 10005| `http://localhost:10005/historical.json` | `http://localhost:10005/recent.json` | `http://localhost:10005/metadata.json` |

### **Legacy Endpoints (ADA Data)**
```
http://localhost:10000/historical.json    # Large historical dataset
http://localhost:10000/recent.json        # Recent data
```

## 📊 **JSON Data Structure (L5 Market Data)**

All JSON endpoints now provide **L5 (top 5 orderbook levels)** data:

```json
{
  "data": [
    {
      "time": "2025-07-29T16:08:32.356180+00:00",
      "price": 3.123,
      "bid": 3.122,
      "ask": 3.124,
      "spread": 0.002,
      "spread_avg_L5_pct": 0.064,  // L5 average spread percentage
      "volume": 152.45,
      "ma_50": 0.065,              // 50-period moving average
      "ma_100": 0.063,             // 100-period moving average  
      "ma_200": 0.062              // 200-period moving average
    }
  ]
}
```

## 🚀 **Usage Examples for Chart Applications**

### **JavaScript/React Example**
```javascript
// Load both historical and recent data for plotting
async function loadCryptoData(crypto = 'ADA') {
  const port = {
    'ADA': 10000, 'BTC': 10001, 'ETH': 10002,
    'SOL': 10003, 'DOT': 10004, 'XRP': 10005
  }[crypto];
  
  try {
    // Load historical data for baseline
    const historicalResponse = await fetch(`http://localhost:${port}/historical.json`);
    const historicalData = await historicalResponse.json();
    
    // Load recent data for real-time updates
    const recentResponse = await fetch(`http://localhost:${port}/recent.json`);
    const recentData = await recentResponse.json();
    
    return {
      historical: historicalData.data,
      recent: recentData.data,
      crypto: crypto
    };
  } catch (error) {
    console.error(`Error loading ${crypto} data:`, error);
  }
}

// Use in your chart component
const chartData = await loadCryptoData('XRP');
```

### **Python Example**
```python
import requests
import pandas as pd

def load_crypto_data(crypto='ADA'):
    port_map = {
        'ADA': 10000, 'BTC': 10001, 'ETH': 10002,
        'SOL': 10003, 'DOT': 10004, 'XRP': 10005
    }
    
    port = port_map[crypto]
    base_url = f"http://localhost:{port}"
    
    # Load historical data
    historical = requests.get(f"{base_url}/historical.json").json()
    recent = requests.get(f"{base_url}/recent.json").json()
    
    # Convert to DataFrame for analysis
    df_hist = pd.DataFrame(historical['data'])
    df_recent = pd.DataFrame(recent['data'])
    
    return df_hist, df_recent

# Usage
historical_df, recent_df = load_crypto_data('XRP')
```

## 🔄 **Real-Time Updates**

- **Historical JSON**: Updates with each new data point
- **Recent JSON**: Contains last 24 hours, updates every second
- **Auto-Generated**: JSON files regenerate automatically as new CSV data arrives

## 🏗️ **For Render Deployment**

When deployed on Render, replace `localhost` with your Render app URL:

```javascript
// Production URLs
const baseUrl = 'https://your-app.onrender.com';
const historicalData = await fetch(`${baseUrl}/historical.json`);
const recentData = await fetch(`${baseUrl}/recent.json`);
```

## ✅ **Status Check**

Test if your endpoints are working:

```bash
# Test XRP endpoints
curl http://localhost:10005/historical.json | head -20
curl http://localhost:10005/recent.json | head -20
curl http://localhost:10005/metadata.json

# Test ADA endpoints  
curl http://localhost:10000/historical.json | head -20
curl http://localhost:10000/recent.json | head -20
```

## 🎯 **Perfect for Chart Libraries**

This setup works perfectly with:
- **Chart.js**: Load historical for baseline, recent for real-time
- **D3.js**: Stream both datasets for advanced visualizations
- **Plotly**: Combine historical trends with recent activity
- **ApexCharts**: Real-time updating with historical context
- **Custom React/Vue charts**: Flexible data format for any visualization

Your chart repository can now simply load both JSONs and have everything it needs for comprehensive crypto data visualization! 🚀