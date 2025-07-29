# 🚀 Render Deployment Guide

## Deploy Your Multi-Cryptocurrency Data Logger to Render.com

This guide will help you deploy your professional multi-crypto data collection system to Render.com for 24/7 operation.

## 📋 Prerequisites

1. **GitHub Repository**: Your code should be in a GitHub repository
2. **Render Account**: Sign up at [render.com](https://render.com) (free tier available)
3. **Basic Git Knowledge**: To push your code to GitHub

## 🎯 Quick Deploy Options

### Option 1: Single Cryptocurrency (Recommended for Free Tier)

Deploy one cryptocurrency logger (uses fewer resources):

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New" → "Web Service"
3. Connect your GitHub repository
4. Use these settings:
   - **Name**: `crypto-data-logger-ada` (or your chosen crypto)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python render_deploy.py`

### Option 2: Multiple Cryptocurrencies (Requires Paid Plan)

Deploy multiple crypto loggers simultaneously:

**Note**: Multiple processes require a paid Render plan ($7/month minimum).

## ⚙️ Configuration Options

### Environment Variables

Set these in your Render service settings:

#### Single Cryptocurrency
```
CRYPTO_SYMBOL = ADA    # Options: ADA, BTC, ETH, SOL, DOT, XRP
```

#### Multiple Cryptocurrencies
```
CRYPTO_SYMBOLS = ADA,BTC,ETH    # Comma-separated list
```

#### Available Cryptocurrencies
- **ADA** (Cardano)
- **BTC** (Bitcoin) 
- **ETH** (Ethereum)
- **SOL** (Solana)
- **DOT** (Polkadot)
- **XRP** (Ripple)

## 🔧 Step-by-Step Deployment

### Step 1: Prepare Your Repository

Ensure these files are in your repository:
- ✅ `requirements.txt` (updated with versions)
- ✅ `render_deploy.py` (deployment script)
- ✅ `render.yaml` (optional, for auto-configuration)
- ✅ All your existing crypto logger files

### Step 2: Push to GitHub

```bash
git add .
git commit -m "Add Render deployment configuration"
git push origin main
```

### Step 3: Deploy on Render

1. **Create New Web Service**:
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New" → "Web Service"
   - Connect your GitHub account and select your repository

2. **Configure Service**:
   ```
   Name: crypto-data-logger
   Environment: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: python render_deploy.py
   ```

3. **Set Environment Variables**:
   - Click "Environment" tab
   - Add environment variable:
     ```
     Key: CRYPTO_SYMBOL
     Value: ADA
     ```
   
4. **Deploy**:
   - Click "Create Web Service"
   - Wait for deployment (usually 2-5 minutes)

### Step 4: Verify Deployment

Once deployed, your service will be available at:
```
https://your-service-name.onrender.com
```

Test endpoints:
- **Status**: `https://your-service-name.onrender.com/`
- **Current Data**: `https://your-service-name.onrender.com/data.csv`
- **Recent JSON**: `https://your-service-name.onrender.com/recent.json`

## 🌐 API Endpoints

Your deployed service provides these endpoints:

```
GET  /                    # Service status and info
GET  /data.csv           # Current CSV data
GET  /recent.json        # Last 24 hours of data
GET  /historical.json    # Complete historical data
GET  /metadata.json      # Dataset metadata
GET  /csv-list          # List all CSV files
GET  /status            # Detailed system status
```

## 💰 Render Pricing & Plans

### Free Tier (Sufficient for Single Crypto)
- ✅ **750 hours/month** of usage
- ✅ **512MB RAM**
- ✅ Perfect for single cryptocurrency logging
- ❌ Service spins down after 15 minutes of inactivity

### Starter Plan ($7/month)
- ✅ **Always-on** service (no spin down)
- ✅ **512MB RAM** 
- ✅ **100GB bandwidth**
- ✅ Suitable for single crypto with high availability

### Standard Plan ($25/month)
- ✅ **2GB RAM**
- ✅ Multiple processes (can run all 6 cryptos)
- ✅ **1TB bandwidth**

## 🔄 Deployment Configurations

### Configuration 1: Single ADA Logger (Free Tier)
```yaml
# Environment Variables
CRYPTO_SYMBOL: ADA

# Resources Used: ~100MB RAM
# Perfect for: Getting started, testing
```

### Configuration 2: Single BTC Logger (Free/Starter)
```yaml
# Environment Variables  
CRYPTO_SYMBOL: BTC

# Resources Used: ~100MB RAM
# Perfect for: Bitcoin-focused data collection
```

### Configuration 3: Multiple Cryptos (Standard Plan)
```yaml
# Environment Variables
CRYPTO_SYMBOLS: ADA,BTC,ETH,XRP

# Resources Used: ~400MB+ RAM
# Perfect for: Professional data collection
```

## 🛠️ Advanced Configuration

### Custom Port Configuration

The deployment script automatically handles Render's port requirements, but you can customize crypto-specific behavior by editing `render_deploy.py`.

### Data Persistence

⚠️ **Important**: Render's ephemeral storage means data files are not permanently stored. For long-term data retention, consider:

1. **Database Integration**: Store data in PostgreSQL (available on Render)
2. **External Storage**: AWS S3, Google Cloud Storage
3. **Download Data Regularly**: Use the API endpoints to backup data

### Environment-Specific Configurations

```python
# Example: Different sample data for production
if os.environ.get('RENDER'):
    # Production settings
    pass
else:
    # Local development settings  
    pass
```

## 🔍 Monitoring & Logs

### View Logs
1. Go to your service dashboard on Render
2. Click "Logs" tab
3. Monitor real-time crypto data collection:
   ```
   ✅ ADA logged to render_app/data/ada/2025-07-29_08.csv
   🚀 Starting ADA server on port 10000
   ```

### Health Monitoring
- Render automatically monitors your service
- Health check endpoint: `/` (shows service status)
- Service will restart automatically if it crashes

## 🚨 Troubleshooting

### Common Issues

#### 1. Service Won't Start
- Check logs for error messages
- Verify environment variables are set correctly
- Ensure `requirements.txt` has all dependencies

#### 2. API Returns Empty Data
- Check if the crypto symbol is valid
- Verify Coinbase API is accessible
- Check logs for data collection errors

#### 3. High Memory Usage
- Switch to single crypto mode
- Upgrade to a higher plan
- Optimize data retention settings

#### 4. Service Spins Down (Free Tier)
- Upgrade to Starter plan for always-on service
- Or accept 15-minute spin-down behavior

### Debug Commands

Check your deployment:
```bash
# Test locally first
python render_deploy.py

# Check crypto configuration
python -c "from config import get_available_cryptos; print(get_available_cryptos())"
```

## 🎯 Production Recommendations

### For Serious Data Collection:
1. **Use Starter Plan** ($7/month) minimum for always-on service
2. **Single Crypto Focus** initially (ADA or BTC recommended)
3. **Set up external storage** for long-term data retention
4. **Monitor regularly** via Render dashboard

### For Professional Use:
1. **Standard Plan** ($25/month) for multiple cryptocurrencies
2. **PostgreSQL database** for data persistence
3. **Custom domain** for API access
4. **Automated backups** to cloud storage

## 📊 Example Live Deployment

Once deployed, your service will provide live cryptocurrency data:

```json
// GET https://your-service.onrender.com/recent.json
{
  "crypto": "ADA",
  "latest_price": 0.8512,
  "data_points": 1440,
  "time_range": "24h",
  "last_updated": "2025-07-29T14:30:00Z"
}
```

## 🔗 Useful Links

- [Render Documentation](https://render.com/docs)
- [Render Python Guide](https://render.com/docs/deploy-flask)
- [Environment Variables](https://render.com/docs/environment-variables)
- [Scaling Services](https://render.com/docs/scaling)

---

**🎉 Your multi-cryptocurrency data logger is now ready for 24/7 operation on Render!**

For support or questions about your specific deployment, check the Render documentation or your service logs.