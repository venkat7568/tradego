# 🔧 Environment Variables Setup (.env file)

This is the **EASIEST and MOST SECURE** way to configure TradeGo!

---

## 🚀 Quick Start (3 Steps)

### Step 1: Copy the Template

```bash
# Copy .env.example to .env
cp .env.example .env

# On Windows PowerShell:
copy .env.example .env
```

### Step 2: Edit the `.env` File

Open `.env` in any text editor:

```bash
# Linux/Mac:
nano .env

# Windows:
notepad .env
```

### Step 3: Fill in Your Credentials

```env
# ==================== UPSTOX API CREDENTIALS ====================
UPSTOX_API_KEY=abc123xyz456
UPSTOX_API_SECRET=def789uvw012
UPSTOX_REDIRECT_URI=http://localhost:8000/callback

# ==================== EMAIL CREDENTIALS ====================
EMAIL_ENABLED=True
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=abcdefghijklmnop
FROM_EMAIL=your-email@gmail.com
TO_EMAIL=your-email@gmail.com
```

**That's it!** ✅

---

## 📝 How to Get Each Credential

### 1️⃣ Upstox API Key & Secret

1. **Go to:** https://account.upstox.com/developer/apps
2. **Login** with your Upstox account
3. **Click:** "Create App"
4. **Fill in:**
   ```
   App Name: TradeGo
   Redirect URI: http://localhost:8000/callback
   ```
   ⚠️ **Important:** If deploying on VPS, use `http://your-vps-ip:8000/callback`
5. **Click:** "Create"
6. **Copy:**
   - **API Key** → Paste as `UPSTOX_API_KEY`
   - **API Secret** → Paste as `UPSTOX_API_SECRET`

### 2️⃣ Gmail App Password

**Why App Password?**
- Gmail doesn't allow regular passwords for apps anymore
- You need to generate a special 16-character "App Password"

**How to Get It:**

1. **Enable 2-Factor Authentication:**
   - Go to: https://myaccount.google.com/security
   - Under "Signing in to Google", click **2-Step Verification**
   - Follow the steps to enable it

2. **Generate App Password:**
   - Go to: https://myaccount.google.com/apppasswords
   - Sign in if prompted
   - Select app: **Mail**
   - Select device: **Other (Custom name)**
   - Type: **TradeGo**
   - Click **Generate**
   - **Copy the 16-character password** (remove spaces!)
   - Example: `abcd efgh ijkl mnop` → `abcdefghijklmnop`

3. **Paste in .env:**
   ```env
   SMTP_USER=your-email@gmail.com
   SMTP_PASSWORD=abcdefghijklmnop
   FROM_EMAIL=your-email@gmail.com
   TO_EMAIL=your-email@gmail.com
   ```

---

## 🔒 Security (VERY IMPORTANT!)

### ✅ What the `.env` File Does:

- Keeps all sensitive credentials in ONE place
- **NOT committed to Git** (protected by `.gitignore`)
- Easy to update without changing code
- Can be different on Windows vs VPS

### ⚠️ NEVER Do This:

❌ **DON'T commit `.env` to GitHub**
```bash
# BAD! Don't do this:
git add .env
git commit -m "add credentials"
```

❌ **DON'T share `.env` file**
- Contains your passwords!
- Keep it private

✅ **DO This:**
```bash
# GOOD! .env is in .gitignore
git status
# Should show: ".env" in "Untracked files" (not staged)
```

---

## 📂 File Structure

```
tradego/
├── .env              ← YOUR credentials (NEVER commit!)
├── .env.example      ← Template (safe to commit)
├── .gitignore        ← Blocks .env from Git
├── config.py         ← Loads from .env automatically
└── ...
```

---

## 🧪 Test Your .env Configuration

### Test 1: Check if .env is Loaded

```python
python -c "import config; print('API Key:', config.UPSTOX_API_KEY[:10] + '...')"
```

Expected output:
```
API Key: abc123xyz4...
```

If you see `your_api_key_here...`, the `.env` file is NOT being loaded!

### Test 2: Check Email Configuration

```python
python -c "import config; print('Email:', config.SMTP_USER)"
```

Expected output:
```
Email: your-email@gmail.com
```

### Test 3: Send Test Email

```bash
python email_notifier.py
```

You should receive 3 test emails!

---

## 🖥️ Different Configurations for Windows & VPS

### For Windows (Local Testing):

**.env**
```env
UPSTOX_REDIRECT_URI=http://localhost:8000/callback
```

### For Ubuntu VPS (Production):

**.env**
```env
UPSTOX_REDIRECT_URI=http://your-vps-ip:8000/callback
```

**Pro Tip:** Keep two files:
- `.env.local` - For Windows testing
- `.env.production` - For VPS

Then copy the right one:
```bash
# On Windows:
cp .env.local .env

# On VPS:
cp .env.production .env
```

---

## 🔧 Advanced: Override Default Settings

You can override ANY setting from `config.py` in your `.env` file:

**.env**
```env
# Capital settings
TOTAL_CAPITAL=2000000
INTRADAY_ALLOCATION=0.80
SWING_ALLOCATION=0.20

# Risk settings
MAX_DAILY_LOSS_PERCENT=0.03
MAX_OPEN_POSITIONS=10

# Callback server
CALLBACK_SERVER_PORT=9000
```

These will override the defaults in `config.py`!

---

## 📚 Optional Environment Variables

The `.env.example` file contains **ALL** possible environment variables. Here are some useful optional ones:

### 🔍 Advanced News Search (Optional)

```env
# Get free API key from: https://brave.com/search/api/
BRAVE_API_KEY=your_brave_api_key_here

# If not set, system uses only Moneycontrol scraping (still works great!)
```

### 📊 Logging Levels (Optional)

```env
# Control how much detail you see in logs (DEBUG, INFO, WARNING, ERROR)
NEWS_LOG_LEVEL=WARNING
TECH_LOG_LEVEL=INFO
OPERATOR_LOG_LEVEL=INFO
```

### 💰 Brokerage Fee Customization (Optional)

```env
# Customize to match your broker's exact fee structure
BROKERAGE_PER_ORDER=20.0
EXCHANGE_TXN_BPS=3.25
STT_DELIVERY_BPS=10.0
STT_INTRADAY_BPS=2.5
STAMP_BPS=1.5
```

### ⚙️ Upstox Technical Settings (Optional)

```env
# How often to refresh instrument list (hours)
UPSTOX_INSTR_MAX_AGE_H=24

# Prefer NSE-only for faster loading (1=yes, 0=all exchanges)
UPSTOX_NSE_ONLY=1

# Cache directory
UPSTOX_CACHE_DIR=./.cache_upstox
```

**All of these are OPTIONAL!** The system works perfectly with just the required credentials (Upstox API + Email).

---

## ❓ Troubleshooting

### Problem 1: `.env` file not found

**Error:**
```
FileNotFoundError: .env file not found
```

**Solution:**
```bash
# Make sure you copied the template
cp .env.example .env
```

### Problem 2: Credentials still showing as `your_api_key_here`

**Solution:**
1. Check `.env` file exists:
   ```bash
   ls -la .env
   ```

2. Check `.env` has correct values (not the template text):
   ```bash
   cat .env | grep UPSTOX_API_KEY
   # Should show your actual API key, not "your_api_key_here"
   ```

3. Restart Python:
   ```bash
   # Exit and restart
   python start_tradego.py
   ```

### Problem 3: Email not sending

**Check:**
1. App Password is 16 characters (no spaces)
2. SMTP_PORT is 587
3. 2FA is enabled on Gmail

**Test SMTP:**
```python
python email_notifier.py
```

---

## 📋 Complete Example

Here's a **REAL example** of what your `.env` should look like (with fake values):

```env
# ==================== UPSTOX API CREDENTIALS ====================
UPSTOX_API_KEY=7a8b9c0d-1e2f-3g4h-5i6j-7k8l9m0n1o2p
UPSTOX_API_SECRET=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
UPSTOX_REDIRECT_URI=http://192.168.1.100:8000/callback

# ==================== EMAIL CREDENTIALS ====================
EMAIL_ENABLED=True
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tradego.alerts@gmail.com
SMTP_PASSWORD=abcdefghijklmnop
FROM_EMAIL=tradego.alerts@gmail.com
TO_EMAIL=your.personal@gmail.com
```

---

## ✅ Setup Complete Checklist

Before running the system, check:

- [ ] `.env` file created (copied from `.env.example`)
- [ ] Upstox API Key added
- [ ] Upstox API Secret added
- [ ] Redirect URI matches Upstox Developer Portal
- [ ] Gmail App Password generated
- [ ] SMTP credentials added
- [ ] Tested: `python -c "import config; print(config.UPSTOX_API_KEY[:10])"`
- [ ] Tested: `python email_notifier.py`
- [ ] Received test emails successfully

**Once all checked, you're ready!** 🚀

---

## 🎯 Next Steps

After setting up `.env`:

1. **Test the system:**
   ```bash
   python start_tradego.py
   ```

2. **Check token flow:**
   - Should send you email if token expired
   - Click link, login, enter PIN
   - System should catch token

3. **Deploy to VPS:**
   - Copy `.env` to VPS
   - Update `UPSTOX_REDIRECT_URI` with VPS IP
   - Run `python start_tradego.py`

---

**That's it bro! Just fill in the `.env` file and you're done! No need to touch `config.py` at all!** ✅
