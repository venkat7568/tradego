# TradeGo Quick Start Guide

## 🚀 Installation & Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Upstox Credentials

Create a `.env` file (copy from `.env.example`):

```bash
cp .env.example .env
```

Edit `.env` and add your Upstox API credentials:

```
UPSTOX_API_KEY=your_api_key_here
UPSTOX_API_SECRET=your_api_secret_here
UPSTOX_REDIRECT_URI=http://localhost:8000/callback
```

### 3. Verify System

```bash
python verify_system.py
```

This checks:
- ✅ All files present
- ✅ Dependencies installed
- ✅ Settings manager working
- ✅ Database ready

---

## 🎮 Running the System

### **Dashboard (MUST RUN FIRST - 24/7)**

```bash
python dashboard.py
```

Open browser: **http://localhost:5000**

The dashboard runs **24/7** and is your **control center** for everything.

---

## ⚙️ Using the Dashboard

### **1. Configure Settings**

Click **⚙️ Settings** button → Modal opens

**Choose Mode:**

#### 📝 **BACKTEST Mode**
- Select date range (From/To)
- Set paper money amount (e.g., ₹100,000)
- Perfect for testing strategies on historical data

#### 📝 **LIVE (Paper) Mode**
- Trades in real market (real-time)
- Uses paper money (e.g., ₹100,000)
- Money is tracked by our system
- No real orders placed

#### 🔴 **LIVE (Real Money) Mode**
- Trades in real market (real-time)
- Uses REAL MONEY from Upstox account
- Real orders are placed
- ⚠️ **BIG WARNING shown in UI**

**Common Settings:**
- Max Open Positions (1-20)
- Max Daily Loss % (0.5-10%)
- Intraday Allocation % (0-100%)
- Swing Allocation % (0-100%)

Click **💾 Save Settings**

### **2. Start Trading System**

Click **▶️ Start** button

The dashboard will:
1. Start the orchestrator.py in background
2. Orchestrator reads settings from dashboard
3. Trading system runs with those settings

### **3. Monitor Real-Time**

Dashboard shows:
- 📊 **Mode Badge** - Current mode (Backtest/Live-Paper/Live-Real)
- 💰 **Capital** - Available capital
- 📈 **Today's P&L** - Profit/Loss
- 🎯 **Win Rate** - Success percentage
- 📋 **Open Trades** - Currently active positions
- 📜 **Closed Trades** - Recent completed trades

**Auto-refreshes every 30 seconds**

### **4. Stop Trading System**

Click **⏹️ Stop** button

Safely stops the orchestrator

---

## 🔄 Complete Workflow

```
1. python dashboard.py (RUNS 24/7)
         ↓
2. Open http://localhost:5000
         ↓
3. Click ⚙️ Settings
         ↓
4. Configure mode & settings
         ↓
5. Click Save Settings
         ↓
6. Click ▶️ Start
         ↓
7. Trading system runs with your settings
         ↓
8. Monitor live in dashboard
         ↓
9. Click ⏹️ Stop when done
```

---

## 📊 Three Trading Modes Explained

### 1️⃣ **BACKTEST** (Safest - Testing)

**What it does:**
- Uses historical market data
- Simulates trades based on past prices
- No real trades, no real money
- Perfect for testing strategies

**Use when:**
- Testing new strategies
- Learning how the system works
- Analyzing past performance
- No risk involved

**Example:**
```
Mode: BACKTEST
From: 2024-01-01
To: 2024-03-31
Capital: ₹500,000 (paper)
```

### 2️⃣ **LIVE (Paper)** (Medium - Real-time Simulation)

**What it does:**
- Connects to LIVE market data (real-time)
- Simulates trades as if they were real
- Tracks P&L with fake money
- NO actual orders placed on broker

**Use when:**
- Testing strategies in real-time
- Learning live market behavior
- No money at risk
- Practicing before going live

**Example:**
```
Mode: LIVE
Type: Paper Money
Capital: ₹1,000,000 (tracked by us)
```

### 3️⃣ **LIVE (Real Money)** (Advanced - Actual Trading)

**What it does:**
- Connects to LIVE market data
- Places REAL orders on Upstox
- Uses REAL money from your Upstox account
- Fetches actual balance from broker

**Use when:**
- Thoroughly tested in backtest mode ✅
- Thoroughly tested in paper mode ✅
- Confident in strategy ✅
- Ready to trade with real money ✅

**Example:**
```
Mode: LIVE
Type: Real Money ⚠️
Capital: Fetched from Upstox
```

---

## 🛡️ Safety Features

### Built-in Protections:

1. **Circuit Breaker**
   - Stops trading if daily loss exceeds limit
   - Default: 2% max daily loss

2. **Position Limits**
   - Maximum open positions at once
   - Default: 5 positions

3. **Mandatory Stop-Loss**
   - Every trade MUST have a stop-loss
   - Prevents unlimited losses

4. **Paper Trading Default**
   - System defaults to BACKTEST mode
   - Requires explicit selection for LIVE mode

5. **Real Money Warning**
   - Big red warning shown in UI
   - Confirmation required

---

## 📁 File Structure

```
tradego/
├── dashboard.py              # 🌐 Dashboard (runs 24/7)
├── orchestrator.py           # 🤖 Trading system (started by dashboard)
├── settings_manager.py       # ⚙️ Settings storage (JSON)
├── templates/
│   └── dashboard.html        # 🎨 Dashboard UI
├── data/
│   ├── trading_settings.json # Your saved settings
│   └── tradego.db           # Trade database
├── pnl_engine.py            # 💰 P&L tracking
├── signal_engine.py         # 📊 Signal generation
├── data_layer.py            # 📈 Market data
├── risk_manager.py          # 🛡️ Risk management
├── upstox_integration.py    # 🔗 Broker integration
└── requirements.txt         # 📦 Dependencies
```

---

## 🐛 Troubleshooting

### Dashboard won't start

```bash
# Check if port 5000 is available
lsof -i :5000  # Linux/Mac
netstat -ano | findstr :5000  # Windows

# Use different port
python dashboard.py --port 5001
```

### Trading system won't start

```bash
# Check settings file
cat data/trading_settings.json

# Check logs
tail -f data/tradego.log
```

### Dependencies missing

```bash
# Install all
pip install -r requirements.txt

# Or install individually
pip install flask schedule psutil pandas beautifulsoup4
```

---

## 📖 Common Tasks

### Test with Backtest Mode

```bash
1. python dashboard.py
2. Open http://localhost:5000
3. Click ⚙️ Settings
4. Select BACKTEST
5. Date: 2024-01-01 to 2024-03-31
6. Capital: ₹500,000
7. Save Settings
8. Click Start
9. Watch results in dashboard
```

### Simulate Live Trading (Safe)

```bash
1. python dashboard.py
2. Click ⚙️ Settings
3. Select LIVE
4. Select Paper Money
5. Capital: ₹1,000,000
6. Save Settings
7. Click Start
8. Monitor in real-time (no real trades)
```

### Go Live with Real Money (Careful!)

```bash
1. Ensure Upstox token is valid (python start_tradego.py)
2. python dashboard.py
3. Click ⚙️ Settings
4. Select LIVE
5. Select Real Money ⚠️
6. Review warning
7. Max Positions: 2 (start small!)
8. Max Daily Loss: 1% (be conservative!)
9. Save Settings
10. Click Start
11. Monitor closely!
```

---

## 🎯 Best Practices

1. **Always start with BACKTEST**
   - Test strategies on historical data first
   - Verify logic works as expected

2. **Graduate to LIVE (Paper)**
   - Test in real-time without risk
   - Ensure real-time data handling works

3. **Start small with LIVE (Real)**
   - Use minimal positions (1-2)
   - Use small capital initially
   - Monitor closely for first few days

4. **Monitor the dashboard**
   - Keep dashboard open 24/7
   - Check trades regularly
   - Review P&L daily

5. **Use circuit breakers**
   - Set conservative daily loss limits
   - Don't override safety features
   - Stop if something seems wrong

---

## 📞 Support

- Check logs: `./data/tradego.log`
- Verify settings: `cat data/trading_settings.json`
- Run verification: `python verify_system.py`

---

## ✅ System is Ready When:

- ✅ `python verify_system.py` passes all checks
- ✅ Dashboard opens at http://localhost:5000
- ✅ Settings modal opens and saves
- ✅ Start button starts orchestrator
- ✅ Trades appear in dashboard

**You're all set! Happy trading! 🚀**
