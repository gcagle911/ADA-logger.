# 📊 Plotting API Guide - Multi-Crypto Data Access

## ✅ Your Repository IS Configured for External Plotting!

Your multi-crypto data logger provides **comprehensive API endpoints** for each cryptocurrency that external plotting applications can easily consume.

## 🌐 **Available API Endpoints Per Cryptocurrency**

### **URL Structure:**
```
https://your-render-app.onrender.com/<endpoint>
http://localhost:<port>/<endpoint>
```

### **Port Mapping:**
| Crypto | Port | Example Base URL |
|--------|------|------------------|
| **ADA** | 10000 | `http://localhost:10000` |
| **BTC** | 10001 | `http://localhost:10001` |
| **ETH** | 10002 | `http://localhost:10002` |
| **SOL** | 10003 | `http://localhost:10003` |
| **DOT** | 10004 | `http://localhost:10004` |
| **XRP** | 10005 | `http://localhost:10005` |

## 📈 **Data Endpoints for Plotting**

### **1. Real-time CSV Data** ✅
```bash
# Current live data in CSV format
GET /<crypto-port>/data.csv

# Examples:
curl http://localhost:10000/data.csv  # ADA data
curl http://localhost:10005/data.csv  # XRP data
```

**CSV Format:**
```csv
timestamp,asset,exchange,price,bid,ask,spread,volume,spread_avg_L5,spread_avg_L5_pct
2025-07-29T14:54:16+00:00,XRP-USD,Coinbase,3.12,3.119,3.121,0.002,45123.45,0.0025,0.08
```

### **2. JSON Endpoints** ✅
```bash
# Real-time JSON data (implemented)
GET /<crypto-port>/metadata.json    # Dataset info
GET /<crypto-port>/index.json       # File index
GET /<crypto-port>/chart-data        # Filtered chart data

# Historical JSON (available via CSV conversion)
GET /<crypto-port>/recent.json      # Last 24h data
GET /<crypto-port>/historical.json  # Complete dataset
```

### **3. Status & Discovery** ✅
```bash
# Service status and available endpoints
GET /<crypto-port>/                  # Full API documentation
GET /<crypto-port>/status           # Service health check
GET /<crypto-port>/csv-list         # Available CSV files
```

## 🔗 **Real-world Examples for Plotting**

### **For ADA (Cardano) Plotting:**
```javascript
// Fetch live ADA data for plotting
const adaData = await fetch('https://your-app.onrender.com/data.csv');
const csvText = await adaData.text();

// Or if running locally:
const adaData = await fetch('http://localhost:10000/data.csv');
```

### **For XRP Plotting:**
```javascript
// Fetch live XRP data
const xrpData = await fetch('http://localhost:10005/data.csv');
const csvText = await xrpData.text();

// Parse CSV for plotting libraries (Chart.js, D3, etc.)
const rows = csvText.split('\n');
const prices = rows.slice(1).map(row => {
    const cols = row.split(',');
    return {
        timestamp: cols[0],
        price: parseFloat(cols[3]),
        volume: parseFloat(cols[7])
    };
});
```

### **Multi-crypto Dashboard:**
```javascript
// Fetch data from multiple cryptos simultaneously
const cryptos = ['ADA', 'BTC', 'ETH', 'XRP'];
const ports = [10000, 10001, 10002, 10005];

const allData = await Promise.all(
    ports.map(port => 
        fetch(`http://localhost:${port}/data.csv`)
            .then(res => res.text())
    )
);
```

## 📊 **Data Format for Plotting**

### **L5 Market Data Structure:**
```javascript
{
    timestamp: "2025-07-29T14:54:16.000Z",
    asset: "XRP-USD",
    exchange: "Coinbase",
    price: 3.12,                    // Mid-price
    bid: 3.119,                     // Best bid
    ask: 3.121,                     // Best ask  
    spread: 0.002,                  // Bid-ask spread
    volume: 45123.45,               // Top 5 levels volume
    spread_avg_L5: 0.0025,          // Average L5 spread
    spread_avg_L5_pct: 0.08         // L5 spread percentage
}
```

### **Perfect for Plotting:**
- ✅ **Price Charts**: Use `price` field for candlestick/line charts
- ✅ **Volume Charts**: Use `volume` field for volume bars
- ✅ **Spread Analysis**: Use `spread_avg_L5_pct` for market quality
- ✅ **Real-time Updates**: Data updates every second
- ✅ **Historical Analysis**: CSV accumulates over time

## 🚀 **Render Deployment URLs**

### **Once Deployed on Render:**
```bash
# Replace 'your-service-name' with your actual Render service name

# ADA endpoints:
https://your-service-name.onrender.com/data.csv      # If deployed with CRYPTO_SYMBOL=ADA
https://your-service-name.onrender.com/status

# Multiple cryptos (if using paid plan):
https://your-ada-service.onrender.com/data.csv       # ADA service
https://your-btc-service.onrender.com/data.csv       # BTC service  
https://your-xrp-service.onrender.com/data.csv       # XRP service
```

## 🛠️ **Integration Examples**

### **Python (pandas/matplotlib):**
```python
import pandas as pd
import requests

# Fetch ADA data
response = requests.get('http://localhost:10000/data.csv')
df = pd.read_csv(StringIO(response.text))

# Plot price over time
df['timestamp'] = pd.to_datetime(df['timestamp'])
df.plot(x='timestamp', y='price', title='ADA Price Chart')
```

### **JavaScript (Chart.js):**
```javascript
// Fetch and plot crypto data
async function plotCrypto(port, cryptoName) {
    const response = await fetch(`http://localhost:${port}/data.csv`);
    const csvText = await response.text();
    
    const data = Papa.parse(csvText, {header: true});
    const chartData = data.data.map(row => ({
        x: row.timestamp,
        y: parseFloat(row.price)
    }));
    
    new Chart('myChart', {
        type: 'line',
        data: {
            datasets: [{
                label: `${cryptoName} Price`,
                data: chartData
            }]
        }
    });
}

// Plot multiple cryptos
plotCrypto(10000, 'ADA');
plotCrypto(10005, 'XRP');
```

### **R (ggplot2):**
```r
library(httr)
library(readr)
library(ggplot2)

# Fetch ADA data
response <- GET("http://localhost:10000/data.csv")
ada_data <- read_csv(content(response, "text"))

# Plot price chart
ggplot(ada_data, aes(x=timestamp, y=price)) +
    geom_line() +
    labs(title="ADA Price Over Time")
```

## 🔄 **Real-time Data Streaming**

### **WebSocket-style Polling:**
```javascript
// Poll for updates every second
setInterval(async () => {
    const response = await fetch('http://localhost:10000/data.csv');
    const csvText = await response.text();
    const rows = csvText.split('\n');
    const latestData = rows[rows.length-2]; // Last row (skip empty final row)
    
    // Update your chart with latest data
    updateChart(latestData);
}, 1000);
```

## ✅ **Summary: Your System IS Ready for Plotting!**

### **What Works Right Now:**
- ✅ **Real-time CSV data** via `/data.csv` endpoints
- ✅ **6 cryptocurrencies** with separate data streams  
- ✅ **L5 market data** (optimized for plotting)
- ✅ **Every second updates** for live charts
- ✅ **CORS enabled** for web applications
- ✅ **Render deployment ready** for public access

### **Plotting Applications Can:**
1. **Fetch live data** from any crypto endpoint
2. **Parse CSV easily** in any programming language
3. **Create real-time charts** with 1-second updates
4. **Build multi-crypto dashboards** using different ports
5. **Access historical data** via accumulated CSV files
6. **Deploy publicly** via Render URLs

### **Example URLs After Render Deployment:**
```
https://ada-logger.onrender.com/data.csv      # ADA data
https://btc-logger.onrender.com/data.csv      # BTC data  
https://xrp-logger.onrender.com/data.csv      # XRP data
```

**Your repository is perfectly configured for external plotting applications to consume real-time cryptocurrency data!** 🚀

The JSON endpoints are being enhanced, but the CSV endpoints provide all the data needed for comprehensive plotting and analysis.