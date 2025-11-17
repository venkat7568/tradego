# TradeGo System Overview

## ✅ What's Built

A **complete automated trading system** with:
- 🌐 **Web Dashboard** (24/7 control center)
- 🤖 **Trading Engine** (orchestrator)
- ⚙️ **UI-driven settings** (no .env editing!)
- 📊 **Real-time monitoring**
- 🛡️ **Safety features**

---

## 🎯 How It Works

```
┌─────────────────────────────────────────────────┐
│  Dashboard (python dashboard.py) - RUNS 24/7   │
│                                                  │
│  http://localhost:5000                          │
│                                                  │
│  - Settings Modal (⚙️ button)                   │
│  - Start/Stop Controls (▶️/⏹️)                  │
│  - Real-time Monitoring                         │
│  - Trade History                                │
│  - P&L Tracking                                 │
└──────────────┬──────────────────────────────────┘
               │
               │ Controls
               │
               ↓
┌─────────────────────────────────────────────────┐
│  Trading System (orchestrator.py)               │
│                                                  │
│  - Reads settings from dashboard                │
│  - Generates signals                            │
│  - Executes trades                              │
│  - Monitors positions                           │
│  - Records P&L                                  │
└─────────────────────────────────────────────────┘
```

---

## 📝 Settings Flow

```
User clicks ⚙️ Settings
      ↓
Modal opens with form
      ↓
User selects:
  - Mode (BACKTEST/LIVE)
  - Live Type (PAPER/REAL)
  - Capital amount
  - Date range (backtest)
  - Max positions
  - Max daily loss %
  - Allocations
      ↓
Click Save Settings
      ↓
Saved to: data/trading_settings.json
      ↓
User clicks ▶️ Start
      ↓
Dashboard starts orchestrator.py
      ↓
Orchestrator reads settings from JSON
      ↓
Trades execute based on those settings
```

---

## 🎮 Three Modes

### 📝 BACKTEST
- **Purpose**: Test strategies on historical data
- **Data**: Past market data
- **Money**: Paper (simulated)
- **Orders**: None (simulated)
- **Use**: Learning, testing, optimizing

### 📝 LIVE (Paper)
- **Purpose**: Real-time simulation
- **Data**: Live market data
- **Money**: Paper (tracked by us, e.g., ₹1L)
- **Orders**: None (simulated)
- **Use**: Practice before going live

### 🔴 LIVE (Real)
- **Purpose**: Actual trading
- **Data**: Live market data
- **Money**: Real (from Upstox account)
- **Orders**: Real orders placed on broker
- **Use**: Making actual profits (or losses!)

---

## 🗂️ Files & Purpose

### **Core System**

| File | Purpose | Always Running? |
|------|---------|----------------|
| `dashboard.py` | Web UI & Control Center | ✅ YES (24/7) |
| `orchestrator.py` | Trading engine | Only when started |
| `settings_manager.py` | Settings storage | Library only |

### **Data Files**

| File | Purpose | Created When |
|------|---------|-------------|
| `data/trading_settings.json` | Your settings | First save |
| `data/tradego.db` | Trade history | First trade |
| `data/tradego.log` | System logs | First run |

### **UI**

| File | Purpose |
|------|---------|
| `templates/dashboard.html` | Dashboard UI with settings modal |

### **Trading Modules**

| File | Purpose |
|------|---------|
| `pnl_engine.py` | Track P&L, manage trades |
| `signal_engine.py` | Generate trading signals |
| `data_layer.py` | Fetch market data |
| `risk_manager.py` | Position sizing, risk checks |
| `upstox_integration.py` | Broker API integration |

---

## 🔑 Key Features

### ✅ **Complete Control from Dashboard**

Everything managed through web UI:
- ✅ Mode selection (Backtest/Live/Paper)
- ✅ Capital settings
- ✅ Risk parameters
- ✅ Start/Stop system
- ✅ Monitor trades
- ✅ View P&L
- ❌ NO .env editing needed!

### ✅ **Safety First**

Built-in protections:
- Circuit breaker (stops at daily loss limit)
- Position limits (max open trades)
- Mandatory stop-loss on every trade
- Default to BACKTEST mode
- Big warning for real money mode

### ✅ **Real-time Monitoring**

Dashboard shows:
- Current mode (Backtest/Live-Paper/Live-Real)
- Available capital
- Today's P&L
- Win rate
- Open positions (live)
- Recent closed trades
- Auto-refreshes every 30 seconds

### ✅ **Flexible Money Management**

Three options:
1. **Backtest**: Paper money for historical testing
2. **Live-Paper**: Paper money for live simulation
3. **Live-Real**: Real money from Upstox

---

## 🚀 Quick Commands

```bash
# Verify everything is ready
python verify_system.py

# Start dashboard (MUST RUN FIRST)
python dashboard.py

# Open in browser
http://localhost:5000

# View logs (in another terminal)
tail -f data/tradego.log

# Check settings
cat data/trading_settings.json
```

---

## 🎯 Typical Usage

### **Development/Testing**
```bash
1. python dashboard.py
2. Open http://localhost:5000
3. Settings → BACKTEST mode
4. Test strategies safely
```

### **Pre-Production**
```bash
1. python dashboard.py
2. Settings → LIVE (Paper) mode
3. Simulate in real market
4. No risk, real-time testing
```

### **Production**
```bash
1. python dashboard.py
2. Settings → LIVE (Real) mode ⚠️
3. Start with small capital
4. Monitor closely 24/7
```

---

## 📊 Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│                    USER (You)                        │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│              WEB BROWSER                             │
│         http://localhost:5000                        │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ Settings │  │  Trades  │  │   P&L    │          │
│  │  Modal   │  │  Table   │  │  Charts  │          │
│  └──────────┘  └──────────┘  └──────────┘          │
│                                                      │
│  [⚙️ Settings]  [▶️ Start]  [⏹️ Stop]               │
└────────────────────┬────────────────────────────────┘
                     │ HTTP API
                     ↓
┌─────────────────────────────────────────────────────┐
│              dashboard.py (Flask)                    │
│                                                      │
│  Routes:                                             │
│  • GET  /api/settings     → Load settings           │
│  • POST /api/settings     → Save settings           │
│  • GET  /api/status       → System status           │
│  • POST /api/system/start → Start orchestrator      │
│  • POST /api/system/stop  → Stop orchestrator       │
│  • GET  /api/portfolio    → Get P&L                 │
│  • GET  /api/trades/open  → Get open trades         │
│  • GET  /api/trades/closed→ Get closed trades       │
└────┬───────────────────────────┬────────────────────┘
     │                           │
     │                           │
     ↓                           ↓
┌──────────────────┐    ┌────────────────────────────┐
│settings_manager.py│    │  orchestrator.py           │
│                   │    │  (subprocess)              │
│ • load_settings() │    │                            │
│ • save_settings() │    │  Reads settings from JSON  │
│                   │    │                            │
│ Stores in:        │    │  ┌──────────────────────┐ │
│ trading_settings  │←───┼─→│   Settings           │ │
│    .json          │    │  └──────────────────────┘ │
└──────────────────┘    │                            │
                        │  ┌──────────────────────┐ │
                        │  │  Signal Generation   │ │
                        │  └──────────────────────┘ │
                        │  ┌──────────────────────┐ │
                        │  │  Risk Management     │ │
                        │  └──────────────────────┘ │
                        │  ┌──────────────────────┐ │
                        │  │  Trade Execution     │ │
                        │  └──────────────────────┘ │
                        │  ┌──────────────────────┐ │
                        │  │  P&L Tracking        │ │
                        │  └──────────────────────┘ │
                        └─────────┬──────────────────┘
                                  │
                                  ↓
                        ┌──────────────────────┐
                        │  Mode Decision:      │
                        │                      │
                        │  BACKTEST?           │
                        │   → Simulate trades  │
                        │                      │
                        │  LIVE-PAPER?         │
                        │   → Simulate + real  │
                        │      market data     │
                        │                      │
                        │  LIVE-REAL?          │
                        │   → Place real orders│
                        │      via Upstox API  │
                        └──────────┬───────────┘
                                   │
                                   ↓
                        ┌──────────────────────┐
                        │   upstox_integration │
                        │   (only LIVE-REAL)   │
                        └──────────┬───────────┘
                                   │
                                   ↓
                        ┌──────────────────────┐
                        │   Upstox Broker      │
                        │   (Real Orders)      │
                        └──────────────────────┘
```

---

## 🎓 Learning Path

### **Week 1: Understand**
- Read QUICKSTART.md
- Run verify_system.py
- Explore dashboard UI
- Try BACKTEST mode

### **Week 2: Test**
- Backtest multiple strategies
- Analyze P&L reports
- Understand win rates
- Refine strategies

### **Week 3: Simulate**
- Switch to LIVE (Paper) mode
- Run for a few days
- Compare backtest vs live results
- Fine-tune settings

### **Week 4: Go Live (Maybe)**
- If confident: LIVE (Real) mode
- Start very small (1-2 positions)
- Monitor constantly
- Scale slowly

---

## 🔐 Security Notes

1. **API Credentials**
   - Store in `.env` file
   - Never commit to git
   - Keep secret

2. **Real Money Mode**
   - Requires explicit selection
   - Shows big warning
   - Fetches real balance
   - Places real orders

3. **Paper Money Mode**
   - Safe for testing
   - No real orders
   - Money tracked locally

---

## 🎉 Summary

**What You Have:**
- ✅ Complete trading system
- ✅ Beautiful web dashboard
- ✅ 3 trading modes (Backtest/Live-Paper/Live-Real)
- ✅ All settings in UI (no .env editing!)
- ✅ Real-time monitoring
- ✅ Safety features
- ✅ Start/Stop from dashboard

**How to Use:**
1. `python dashboard.py` (runs 24/7)
2. Open `http://localhost:5000`
3. Configure settings via UI
4. Start trading system
5. Monitor in real-time!

**It's that simple! 🚀**
