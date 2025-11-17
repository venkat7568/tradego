"""
Trading settings storage - Managed via dashboard UI
"""

import json
import os
from datetime import date
from typing import Dict, Any

SETTINGS_FILE = './data/trading_settings.json'

DEFAULT_SETTINGS = {
    'mode': 'BACKTEST',  # LIVE or BACKTEST
    'live_type': 'PAPER',  # PAPER or REAL (for LIVE mode)
    'capital': 1000000,  # Starting capital for paper trading
    'backtest_from': None,  # For backtesting date range
    'backtest_to': None,
    'max_positions': 5,
    'max_daily_loss_percent': 2.0,
    'intraday_allocation': 0.7,
    'swing_allocation': 0.3,
    'auto_trade': False,  # Auto-trading enabled/disabled
    'last_updated': None
}


def load_settings() -> Dict[str, Any]:
    """Load trading settings from file"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                # Merge with defaults to ensure all keys exist
                return {**DEFAULT_SETTINGS, **settings}
        except Exception as e:
            print(f"Error loading settings: {e}")
            return DEFAULT_SETTINGS.copy()
    return DEFAULT_SETTINGS.copy()


def save_settings(settings: Dict[str, Any]) -> bool:
    """Save trading settings to file"""
    try:
        # Ensure data directory exists
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)

        # Add timestamp
        from datetime import datetime
        settings['last_updated'] = datetime.now().isoformat()

        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving settings: {e}")
        return False


def get_setting(key: str, default=None):
    """Get a specific setting"""
    settings = load_settings()
    return settings.get(key, default)


def update_setting(key: str, value: Any) -> bool:
    """Update a specific setting"""
    settings = load_settings()
    settings[key] = value
    return save_settings(settings)
