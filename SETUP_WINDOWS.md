# TradeGo - Windows 11 Setup Guide

## Prerequisites

1. **Python 3.11+**
   - Download from: https://www.python.org/downloads/
   - During installation, CHECK ☑️ "Add Python to PATH"

2. **Git** (optional, for cloning repo)
   - Download from: https://git-scm.com/download/win

## Installation Steps

### Step 1: Clone/Download Repository

```powershell
# Option A: Using Git
git clone https://github.com/venkat7568/tradego.git
cd tradego

# Option B: Download ZIP and extract
# Then open PowerShell in the tradego folder
```

### Step 2: Create Virtual Environment (Recommended)

```powershell
# Create virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1

# If you get execution policy error, run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Step 3: Install Dependencies

```powershell
# Upgrade pip
python -m pip install --upgrade pip

# Install requirements
pip install -r requirements.txt
```

**Note:** If `ta-lib` fails to install (it's optional), comment it out in `requirements.txt` and continue. The system uses manual indicator calculations.

### Step 4: Create Data Directory

```powershell
mkdir data
```

### Step 5: Test the System

```powershell
# Test P&L Engine
python pnl_engine.py

# You should see:
# ✅ Created trade: NSE_EQ|RELIANCE-EQ_...
# ✅ Trade closed: P&L: ₹4950.00
# ✅ P&L Engine test complete!
```

### Step 6: Run the System

```powershell
# Start the orchestrator
python orchestrator.py
```

You should see:
```
🚀 TradeGo System Starting...
   Capital: ₹10,00,000
   Intraday: 70%
   Swing: 30%
   Max Positions: 5
   Max Daily Loss: 2%

✅ System ready. Waiting for market hours...
```

## Testing on Windows

The system will:
- ✅ Run in paper trading mode (no real orders)
- ✅ Generate signals during market hours (9:15 AM - 3:30 PM IST)
- ✅ Track P&L in SQLite database (`./data/tradego.db`)
- ✅ Log everything to `./data/tradego.log`

## Checking Logs

```powershell
# View live logs
Get-Content ./data/tradego.log -Wait

# Or open in Notepad
notepad ./data/tradego.log
```

## Stopping the System

Press `Ctrl + C` in the PowerShell window

## Common Issues

### 1. Python not found
```
Solution: Reinstall Python and check "Add to PATH" option
```

### 2. pip install fails
```powershell
# Solution: Update pip
python -m pip install --upgrade pip
```

### 3. Module not found errors
```powershell
# Solution: Make sure virtual environment is activated
.\venv\Scripts\Activate.ps1

# Then reinstall
pip install -r requirements.txt
```

### 4. Permission denied errors
```powershell
# Solution: Run PowerShell as Administrator
# Right-click PowerShell → Run as Administrator
```

## What to Check After Running

1. **Database created**: `./data/tradego.db` should exist
2. **Logs created**: `./data/tradego.log` should have entries
3. **No errors**: Check logs for any ERROR messages

## Next Steps

Once testing on Windows is successful:
1. ✅ Verify P&L tracking is accurate
2. ✅ Check signal generation works
3. ✅ Monitor for any crashes or errors
4. ✅ Run for a few days in paper mode

Then deploy to Ubuntu VPS for 24/7 operation (see `SETUP_UBUNTU.md`)

## Configuration

Edit `config.py` to change:
- Capital amount
- Risk percentages
- Max positions
- Circuit breaker limits

## Need Help?

Check the logs first:
```powershell
Get-Content ./data/tradego.log | Select-String "ERROR"
```

This will show all error messages.
