"""
Configuration file for TradeGo system
"""

import os

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

# ==================== UPSTOX API SETTINGS ====================
# Get these from Upstox Developer Portal: https://account.upstox.com/developer/apps

# Method 1: Set in environment variables (RECOMMENDED for security)
UPSTOX_API_KEY = os.getenv('UPSTOX_API_KEY', 'your_api_key_here')
UPSTOX_API_SECRET = os.getenv('UPSTOX_API_SECRET', 'your_api_secret_here')

# Redirect URI for OAuth callback
# For VPS: http://your-vps-ip:8000/callback
# For local testing: http://localhost:8000/callback
UPSTOX_REDIRECT_URI = os.getenv('UPSTOX_REDIRECT_URI', 'http://localhost:8000/callback')

# Callback server port
CALLBACK_SERVER_PORT = 8000

# ==================== EMAIL SETTINGS (for token refresh alerts) ====================
# SMTP Settings - For Gmail (or use your SMTP provider)

# IMPORTANT: For Gmail, you need to:
# 1. Enable 2-factor authentication
# 2. Generate an "App Password": https://myaccount.google.com/apppasswords
# 3. Use the App Password (not your regular Gmail password)

EMAIL_ENABLED = os.getenv('EMAIL_ENABLED', 'True').lower() == 'true'

# SMTP Configuration
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))

# Your email credentials
SMTP_USER = os.getenv('SMTP_USER', 'your-email@gmail.com')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', 'your-app-password')  # Use App Password for Gmail

# Email addresses
FROM_EMAIL = os.getenv('FROM_EMAIL', 'your-email@gmail.com')
TO_EMAIL = os.getenv('TO_EMAIL', 'your-email@gmail.com')  # Where to send alerts

# Send daily report at market close
SEND_DAILY_REPORT = True
DAILY_REPORT_TIME = "15:35"  # 3:35 PM IST

# ==================== DATABASE ====================
DATABASE_PATH = "./data/tradego.db"
TOKEN_FILE = "./data/upstox_token.json"

# ==================== LOGGING ====================
LOG_FILE = "./data/tradego.log"
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR

# ==================== ADVANCED SETTINGS ====================
# Token check time (every morning before market open)
TOKEN_CHECK_TIME = "08:50"  # 8:50 AM IST

# Authorization timeout (how long to wait for user to click email link)
AUTHORIZATION_TIMEOUT = 600  # 10 minutes

# Enable/disable features
ENABLE_CALLBACK_SERVER = True
ENABLE_EMAIL_ALERTS = EMAIL_ENABLED
