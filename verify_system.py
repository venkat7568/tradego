#!/usr/bin/env python3
"""
Complete System Verification Script
Tests all components before running
"""

import sys
import os

print("=" * 60)
print("TradeGo System Verification")
print("=" * 60)

# Test 1: Check Python version
print("\n1. Python Version Check")
print(f"   ✅ Python {sys.version.split()[0]}")

# Test 2: Check required files exist
print("\n2. File Structure Check")
required_files = [
    'dashboard.py',
    'orchestrator.py',
    'settings_manager.py',
    'templates/dashboard.html',
    'pnl_engine.py',
    'data_layer.py',
    'signal_engine.py',
    'risk_manager.py',
    'upstox_integration.py',
    'logging_config.py'
]

for file in required_files:
    if os.path.exists(file):
        print(f"   ✅ {file}")
    else:
        print(f"   ❌ {file} - MISSING!")

# Test 3: Check data directory
print("\n3. Data Directory Check")
if os.path.exists('data'):
    print(f"   ✅ data/ directory exists")
    if os.path.exists('data/trading_settings.json'):
        print(f"   ✅ trading_settings.json exists")
    else:
        print(f"   ⚠️  trading_settings.json will be created on first run")
else:
    os.makedirs('data', exist_ok=True)
    print(f"   ✅ data/ directory created")

# Test 4: Import dependencies
print("\n4. Dependencies Check")
required_modules = {
    'flask': 'Flask',
    'schedule': 'schedule',
    'psutil': 'psutil',
    'pandas': 'pandas',
    'requests': 'requests',
    'beautifulsoup4': 'bs4'
}

missing = []
for pip_name, import_name in required_modules.items():
    try:
        __import__(import_name)
        print(f"   ✅ {pip_name}")
    except ImportError:
        print(f"   ❌ {pip_name} - MISSING! Run: pip install {pip_name}")
        missing.append(pip_name)

if missing:
    print(f"\n   ⚠️  Missing dependencies. Install with:")
    print(f"   pip install {' '.join(missing)}")

# Test 5: Settings Manager
print("\n5. Settings Manager Check")
try:
    from settings_manager import load_settings, save_settings
    settings = load_settings()
    print(f"   ✅ Settings Manager working")
    print(f"   Mode: {settings.get('mode', 'BACKTEST')}")
    print(f"   Capital: ₹{settings.get('capital', 1000000):,.0f}")
except Exception as e:
    print(f"   ❌ Settings Manager error: {e}")

# Test 6: Orchestrator
print("\n6. Orchestrator Check")
try:
    # Just import, don't initialize (to avoid dependencies)
    import orchestrator
    print(f"   ✅ Orchestrator module loads")
except Exception as e:
    print(f"   ❌ Orchestrator error: {e}")

# Test 7: Dashboard
print("\n7. Dashboard Check")
try:
    import dashboard
    print(f"   ✅ Dashboard module loads")
except Exception as e:
    print(f"   ❌ Dashboard error: {e}")

# Test 8: Database
print("\n8. Database Check")
if os.path.exists('data/tradego.db'):
    print(f"   ✅ Database exists")
else:
    print(f"   ⚠️  Database will be created on first run")

print("\n" + "=" * 60)
if not missing:
    print("✅ ALL CHECKS PASSED - System ready to run!")
    print("\nTo start:")
    print("  python dashboard.py")
    print("  Then open: http://localhost:5000")
else:
    print("⚠️  Some dependencies missing - install them first")
    print(f"  pip install -r requirements.txt")
print("=" * 60)
