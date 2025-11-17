# TradeGo Dashboard & Trading Modes

## Overview

TradeGo now supports:
1. **LIVE** and **BACKTEST** trading modes
2. Real balance fetching from Upstox
3. Real order placement through Upstox
4. Web dashboard for real-time monitoring

---

## Trading Modes

### BACKTEST Mode (Default)
- **Paper trading** - No real money involved
- Trades are simulated in the database
- Perfect for testing strategies
- Safe for development and learning

### LIVE Mode
- **Real trading** with real money
- Places actual orders on Upstox
- Fetches real balance from your broker account
- Requires valid Upstox API credentials and token

---

## Configuration

Edit your `.env` file:

```bash
# Trading Mode: LIVE or BACKTEST
TRADING_MODE=BACKTEST  # Change to LIVE for real trading

# Fetch live balance from Upstox (only applies in LIVE mode)
FETCH_LIVE_BALANCE=False  # Change to True to fetch real balance
```

### Safety Features

1. **Default to BACKTEST**: System defaults to BACKTEST mode for safety
2. **Explicit LIVE activation**: You must explicitly set `TRADING_MODE=LIVE`
3. **Independent balance fetching**: Even in LIVE mode, balance fetching is optional
4. **Mandatory stop-loss**: Every live order requires a stop-loss

---

## Web Dashboard

### Starting the Dashboard

```bash
python dashboard.py
```

The dashboard will be available at: `http://localhost:5000`

### Features

1. **Real-time Monitoring**
   - Current trading mode (LIVE/BACKTEST)
   - Portfolio P&L (realized and unrealized)
   - Open positions
   - Recent closed trades
   - Win rate and profit factor

2. **Capital Display**
   - Shows live balance from Upstox (if configured)
   - Falls back to config capital in BACKTEST mode

3. **Trade Details**
   - Entry/exit prices
   - Stop-loss and target levels
   - Strategy attribution
   - Performance metrics

4. **Auto-refresh**
   - Updates every 30 seconds
   - Manual refresh button available

### Access from Other Devices

To access the dashboard from other devices on your network:

```bash
# Find your IP address
# Linux/Mac:
ifconfig | grep "inet "

# Windows:
ipconfig

# Then access: http://YOUR_IP:5000
```

---

## Usage Examples

### Example 1: Backtesting (Safe Testing)

```bash
# 1. Set mode in .env
TRADING_MODE=BACKTEST
FETCH_LIVE_BALANCE=False

# 2. Start dashboard (optional)
python dashboard.py

# 3. Start trading system
python orchestrator.py
```

### Example 2: Live Trading with Config Capital

```bash
# 1. Set mode in .env
TRADING_MODE=LIVE
FETCH_LIVE_BALANCE=False  # Use config capital

# 2. Ensure you have valid token
python start_tradego.py

# 3. Start dashboard
python dashboard.py

# 4. Start trading system
python orchestrator.py
```

### Example 3: Live Trading with Real Balance

```bash
# 1. Set mode in .env
TRADING_MODE=LIVE
FETCH_LIVE_BALANCE=True  # Fetch real balance from Upstox

# 2. Ensure you have valid token
python start_tradego.py

# 3. Start dashboard
python dashboard.py

# 4. Start trading system
python orchestrator.py
```

---

## API Endpoints

The dashboard provides RESTful API endpoints:

### System Status
```
GET /api/status
```
Returns: Trading mode, capital, limits, timestamp

### Portfolio Metrics
```
GET /api/portfolio
```
Returns: P&L, win rate, profit factor, portfolio heat

### Open Trades
```
GET /api/trades/open
```
Returns: List of currently open positions

### Closed Trades
```
GET /api/trades/closed?days=7
```
Returns: Recently closed trades (default: last 7 days)

### Upstox Live Balance
```
GET /api/upstox/balance
```
Returns: Live funds from Upstox (requires valid token)

### Upstox Live Positions
```
GET /api/upstox/positions
```
Returns: Live positions from Upstox (requires valid token)

---

## Safety Checklist

Before going LIVE:

- [ ] Test thoroughly in BACKTEST mode
- [ ] Verify all strategies are working correctly
- [ ] Check stop-loss calculations
- [ ] Confirm position sizing logic
- [ ] Set appropriate risk limits in `config.py`
- [ ] Have valid Upstox token
- [ ] Start with small capital
- [ ] Monitor closely for the first few days

---

## Troubleshooting

### Dashboard not loading
```bash
# Check if Flask is installed
pip install Flask==3.0.0

# Check if port 5000 is available
# Linux/Mac: lsof -i :5000
# Windows: netstat -ano | findstr :5000
```

### Live orders not placing
1. Check if Upstox token is valid: `python start_tradego.py`
2. Verify `TRADING_MODE=LIVE` in `.env`
3. Check orchestrator logs in `./data/tradego.log`
4. Ensure market is open

### Balance not fetching
1. Verify `FETCH_LIVE_BALANCE=True` in `.env`
2. Check Upstox token validity
3. Ensure network connectivity
4. Check API response in logs

---

## Architecture

```
orchestrator.py
├── Trading Mode: LIVE or BACKTEST
├── Balance Source: Upstox API or Config
└── Order Placement:
    ├── LIVE: upstox_operator.place_order()
    └── BACKTEST: pnl_engine.create_trade()

dashboard.py
├── Flask Web Server
├── REST API Endpoints
└── Real-time UI Updates
```

---

## Performance Monitoring

### Via Dashboard
- Open `http://localhost:5000` in your browser
- Monitor in real-time

### Via Logs
```bash
# View logs
tail -f ./data/tradego.log

# Filter for trades
grep "Trade" ./data/tradego.log

# Filter for P&L
grep "P&L" ./data/tradego.log
```

### Via Database
```bash
# View trades in SQLite
sqlite3 ./data/tradego.db

# Example queries:
SELECT * FROM trades WHERE status='OPEN';
SELECT * FROM trades WHERE status='CLOSED' ORDER BY exit_time DESC LIMIT 10;
SELECT symbol, SUM(net_pnl) as total_pnl FROM trades GROUP BY symbol;
```

---

## Next Steps

1. **Test in BACKTEST mode**
   - Run for several days
   - Analyze performance
   - Refine strategies

2. **Paper trade verification**
   - Compare paper trades with market
   - Verify signal quality
   - Check timing and execution

3. **Go LIVE gradually**
   - Start with 1-2 positions max
   - Use small capital
   - Monitor closely
   - Scale up slowly

---

## Support

For issues or questions:
1. Check logs: `./data/tradego.log`
2. Review configuration: `.env` and `config.py`
3. Test API connectivity: `python upstox_integration.py`
4. Verify token: `python start_tradego.py`

---

## Disclaimer

⚠️ **IMPORTANT**: Live trading involves real financial risk. The developers are not responsible for any financial losses. Always:
- Test thoroughly before going live
- Start with small amounts
- Use proper risk management
- Monitor your trades closely
- Never risk more than you can afford to lose
