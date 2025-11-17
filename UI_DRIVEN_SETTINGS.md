# UI-Driven Settings - Complete System

## 🎯 Goal: All settings managed through Dashboard UI

Instead of editing `.env` files, users can now manage all trading settings directly from the web dashboard.

## ✅ What's Implemented

### 1. Settings Manager (`settings_manager.py`)
- Stores settings in `./data/trading_settings.json`
- Default settings include:
  - `mode`: 'LIVE' or 'BACKTEST'
  - `live_type`: 'PAPER' or 'REAL' (for LIVE mode)
  - `capital`: Starting capital amount
  - `backtest_from` / `backtest_to`: Date range for backtesting
  - `max_positions`: Maximum open positions
  - `max_daily_loss_percent`: Circuit breaker %
  - `intraday_allocation` / `swing_allocation`: Capital split
  - `auto_trade`: Enable/disable auto-trading

### 2. Dashboard API Endpoints (`dashboard.py`)
- `GET /api/settings` - Get current settings
- `POST /api/settings` - Update settings
- `POST /api/system/start` - Start trading system
- `POST /api/system/stop` - Stop trading system
- Updated `/api/status` to use settings instead of .env

### 3. Process Management
- Dashboard can start/stop the orchestrator
- Checks if trading system is running
- Manages process lifecycle

## 🎨 UI Design (To Be Added to dashboard.html)

### Settings Panel Features:

```
┌─────────────────────────────────────┐
│  ⚙️  Trading Settings               │
├─────────────────────────────────────┤
│                                      │
│  Trading Mode:                       │
│  ○ Live Trading  ○ Backtest │
│                                      │
│  [If Live Selected]                  │
│    Money Type:                       │
│    ○ Real Money  ○ Paper Trading    │
│    Capital: ₹ [1000000]             │
│                                      │
│  [If Backtest Selected]              │
│    From Date: [2024-01-01]          │
│    To Date:   [2024-12-31]          │
│    Capital: ₹ [1000000]             │
│                                      │
│  Risk Settings:                      │
│    Max Positions: [5]                │
│    Max Daily Loss: [2]%              │
│    Intraday Allocation: [70]%        │
│    Swing Allocation: [30]%           │
│                                      │
│  │ Save Settings | [Reset]         │
│                                      │
│  System Control:                     │
│  Status: ● Running / ○ Stopped      │
│  │ Start Trading | [Stop Trading] │
└─────────────────────────────────────┘
```

## 📝 Next Steps (To Complete)

### 1. Update `dashboard.html`
Add settings panel with:
- Mode selector (Live/Backtest)
- Live type selector (Real/Paper) - shows only if Live mode
- Date range picker - shows only if Backtest mode
- Capital input
- Risk settings (max positions, daily loss %, allocations)
- Save/Reset buttons
- System start/stop buttons with status indicator

### 2. Update `orchestrator.py`
Change from `config` to `settings_manager`:
```python
# Old:
from config import TRADING_MODE, TOTAL_CAPITAL
self.trading_mode = TRADING_MODE

# New:
from settings_manager import load_settings
self.settings = load_settings()
self.trading_mode = self.settings['mode']
self.live_type = self.settings['live_type']
```

Replace all `config.XXXXX` references with `self.settings['xxxxx']`

### 3. Clean up `.env.example`
Remove:
- `TRADING_MODE`
- `FETCH_LIVE_BALANCE`
- `MODE`
- `STRICT_LIVE_MODE`

Keep only:
- Upstox API credentials
- Email settings
- Technical/logging settings

## 🚀 How It Works

1. **User opens dashboard** → See current settings
2. **Changes settings in UI** → POST /api/settings
3. **Settings saved** → `./data/trading_settings.json`
4. **Clicks "Start Trading"** → POST /api/system/start
5. **Dashboard starts orchestrator** → Reads settings from JSON
6. **Orchestrator runs** → Uses UI-configured settings
7. **User monitors in real-time** → Dashboard shows live status

## 💡 Benefits

✅ **No more .env editing** - Everything in one place
✅ **Visual controls** - See what you're changing
✅ **Live updates** - Change settings without restarting
✅ **Safety features** - Clear indicators for real money trading
✅ **Date range backtesting** - Easy historical testing
✅ **Process control** - Start/stop from UI

## 🎯 User Flow Examples

### Example 1: Backtest a Strategy
1. Open dashboard
2. Select "Backtest" mode
3. Set date range: 2024-01-01 to 2024-03-31
4. Set capital: ₹500,000
5. Click "Save Settings"
6. Click "Start Trading"
7. Monitor results in dashboard

### Example 2: Paper Trading (Live Simulation)
1. Select "Live Trading" mode
2. Select "Paper Trading"
3. Set capital: ₹1,000,000
4. Adjust risk settings
5. Click "Save Settings"
6. Click "Start Trading"
7. System simulates live trading without real money

### Example 3: Real Money Trading
1. Select "Live Trading" mode
2. Select "Real Money" ⚠️
3. Capital is fetched from Upstox automatically
4. Review all settings carefully
5. Click "Save Settings"
6. Click "Start Trading" (requires confirmation)
7. System places real orders with real money

## ⚠️ Safety Features

- **Default to BACKTEST**: System always starts in backtest mode
- **Explicit Real Money Selection**: User must actively choose "Real Money"
- **Confirmation Dialogs**: Extra confirmation for real money trading
- **Visual Indicators**: Red warnings for real money mode
- **Process Monitoring**: Dashboard shows if system is running
- **Emergency Stop**: Big red stop button always visible

## 📦 Files Changed

- ✅ `settings_manager.py` - Settings storage and retrieval
- ✅ `dashboard.py` - API endpoints and process management
- 🔄 `dashboard.html` - UI needs to be updated (next step)
- 🔄 `orchestrator.py` - Needs to use settings_manager (next step)
- 🔄 `.env.example` - Clean up unnecessary variables (next step)

## 🔧 Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| Settings Manager | ✅ Done | Fully functional |
| Dashboard API | ✅ Done | All endpoints working |
| Process Management | ✅ Done | Start/stop implemented |
| Dashboard UI | 🔄 Pending | Needs settings panel |
| Orchestrator Integration | 🔄 Pending | Needs refactoring |
| .env Cleanup | 🔄 Pending | Remove unused vars |

---

**Next Session**: Complete the dashboard UI with settings panel and update orchestrator to use settings_manager.
