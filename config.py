"""
Configuration file for TradeGo system
"""

# Capital & Risk Settings
TOTAL_CAPITAL = 1_000_000  # ₹10 Lakh
INTRADAY_ALLOCATION = 0.70  # 70%
SWING_ALLOCATION = 0.30  # 30%

# Risk Limits
MIN_RISK_PER_TRADE = 0.005  # 0.5%
MAX_RISK_PER_TRADE = 0.010  # 1.0%
MAX_OPEN_POSITIONS = 5
MAX_PORTFOLIO_HEAT = 0.03  # 3%
MAX_CAPITAL_DEPLOYED = 0.50  # 50%

# Circuit Breakers
MAX_DAILY_LOSS_PERCENT = 0.02  # 2%
MAX_WEEKLY_LOSS_PERCENT = 0.05  # 5%

# Market Hours (IST)
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 15
MARKET_CLOSE_HOUR = 15
MARKET_CLOSE_MINUTE = 30

# Trading Schedule
MAIN_LOOP_INTERVAL_MINUTES = 15
POSITION_MONITOR_INTERVAL_SECONDS = 30

# Strategy Settings
MIN_CONFIDENCE_THRESHOLD = 0.65
MIN_RR_RATIO_INTRADAY = 1.5
MIN_RR_RATIO_SWING = 1.2

# Upstox API (set these in environment variables for security)
# UPSTOX_API_KEY = "your_api_key"
# UPSTOX_API_SECRET = "your_api_secret"
# UPSTOX_ACCESS_TOKEN = "your_access_token"

# Database
DATABASE_PATH = "./data/tradego.db"

# Logging
LOG_FILE = "./data/tradego.log"
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
