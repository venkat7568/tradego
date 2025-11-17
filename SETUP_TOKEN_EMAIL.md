# 🔐 TradeGo - Token & Email Setup Guide

This guide shows you how to set up **automatic token refresh** with **email notifications**.

---

## 📧 How It Works

### **The Problem:**
Upstox API tokens expire every 24 hours. You need to manually login and get a new token daily.

### **The Solution:**
TradeGo automates this with email + OAuth callback:

```
8:50 AM → System checks token
          ↓
      Token expired?
          ↓
      YES → Send you email with "Authorize" link
          ↓
      You click link → Upstox login → Enter PIN
          ↓
      Upstox redirects back to TradeGo callback server
          ↓
      System catches new token automatically
          ↓
      Saves token and resumes trading
```

**You only need to click ONE link in your email every morning!** ✅

---

## 🚀 Part 1: Upstox API Setup

### Step 1: Create Upstox Developer App

1. **Go to Upstox Developer Portal:**
   https://account.upstox.com/developer/apps

2. **Login** with your Upstox credentials

3. **Click "Create App"**

4. **Fill in details:**
   ```
   App Name: TradeGo
   Redirect URI: http://your-vps-ip:8000/callback

   (For testing on Windows: http://localhost:8000/callback)
   ```

5. **Click "Create"**

6. **Copy these values:**
   - **API Key** (client_id)
   - **API Secret** (client_secret)

---

## 📧 Part 2: Gmail SMTP Setup (for Email Alerts)

### Step 1: Enable 2-Factor Authentication

1. Go to: https://myaccount.google.com/security
2. Under "Signing in to Google", click **2-Step Verification**
3. Follow steps to enable 2FA

### Step 2: Generate App Password

1. Go to: https://myaccount.google.com/apppasswords
2. Sign in if prompted
3. In "Select app", choose **Mail**
4. In "Select device", choose **Other (Custom name)**
5. Enter: **TradeGo**
6. Click **Generate**
7. **Copy the 16-character password** (it will look like: `abcd efgh ijkl mnop`)

⚠️ **IMPORTANT:** Use this App Password, NOT your regular Gmail password!

---

## ⚙️ Part 3: Configure TradeGo

### Option 1: Edit `config.py` Directly

Open `config.py` and update:

```python
# Upstox API
UPSTOX_API_KEY = 'your-api-key-here'
UPSTOX_API_SECRET = 'your-api-secret-here'
UPSTOX_REDIRECT_URI = 'http://your-vps-ip:8000/callback'

# Email Settings
SMTP_USER = 'your-email@gmail.com'
SMTP_PASSWORD = 'your-16-char-app-password'  # No spaces!
FROM_EMAIL = 'your-email@gmail.com'
TO_EMAIL = 'your-email@gmail.com'
```

### Option 2: Use Environment Variables (More Secure)

**On Ubuntu VPS:**
```bash
# Edit systemd service file
sudo nano /etc/systemd/system/tradego.service

# Add these lines under [Service]:
Environment="UPSTOX_API_KEY=your-api-key"
Environment="UPSTOX_API_SECRET=your-api-secret"
Environment="UPSTOX_REDIRECT_URI=http://your-vps-ip:8000/callback"
Environment="SMTP_USER=your-email@gmail.com"
Environment="SMTP_PASSWORD=your-app-password"
Environment="FROM_EMAIL=your-email@gmail.com"
Environment="TO_EMAIL=your-email@gmail.com"

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart tradego
```

**On Windows (PowerShell):**
```powershell
# Set environment variables temporarily
$env:UPSTOX_API_KEY="your-api-key"
$env:UPSTOX_API_SECRET="your-api-secret"
$env:UPSTOX_REDIRECT_URI="http://localhost:8000/callback"
$env:SMTP_USER="your-email@gmail.com"
$env:SMTP_PASSWORD="your-app-password"
$env:FROM_EMAIL="your-email@gmail.com"
$env:TO_EMAIL="your-email@gmail.com"

# Then run
python orchestrator.py
```

---

## 🧪 Part 4: Test the System

### Test 1: Test Email Notifier

```python
python email_notifier.py
```

Expected output:
```
Test 1: Token Refresh Email
  Result: ✓ Sent

Check your email! You should receive:
- Subject: "🔑 TradeGo - Upstox Token Refresh Required"
- With green "Authorize" button
```

### Test 2: Test Token Manager

```python
python token_manager.py
```

Expected flow:
```
1. Token valid: False
2. Starting callback server...
3. Authorization URL: https://api.upstox.com/...
4. Please open the URL in your browser
5. Waiting for authorization...

[Open URL in browser]
[Login to Upstox]
[Enter PIN]
[Redirected back to localhost:8000/callback]

✅ Token obtained successfully!
   Access Token: eyJ...
   Expires: 2025-11-18 08:50:00
```

### Test 3: Run Full System

```bash
python orchestrator.py
```

Expected flow:
```
🚀 TradeGo System Starting...
   Capital: ₹10,00,000
   Intraday: 70%
   Swing: 30%

🔐 Checking Upstox token...
⚠️  Token expired or not found

📧 Sending token refresh email...
✅ Email sent to: your-email@gmail.com

🌐 Starting callback server on port 8000...
⏳ Waiting for authorization (timeout: 10 minutes)...

[Check your email and click the "Authorize" button]
[Login to Upstox and enter PIN]

✅ Authorization complete!
✅ System ready. Trading will start at 9:15 AM...
```

---

## 📬 What Emails You'll Receive

### 1. Daily Token Refresh (Every Morning at 8:50 AM)

**Subject:** 🔑 TradeGo - Upstox Token Refresh Required

**Content:**
```
Your Upstox access token has expired.

Action Required: Click the button below to authorize TradeGo.

[🔓 Authorize TradeGo] ← Click this button

What will happen:
1. You'll be redirected to Upstox login page
2. Enter your Upstox credentials and PIN
3. Upstox will redirect back to TradeGo
4. Trading will resume automatically
```

### 2. Daily P&L Report (Every Evening at 3:35 PM)

**Subject:** 📊 TradeGo Daily Report - 2025-11-17

**Content:**
```
📈 Total P&L: ₹12,450

Intraday P&L:  ₹11,600
Swing P&L:     ₹850
Total Trades:  8
Win Rate:      75.0%
```

### 3. Alerts (Circuit Breaker, Errors, etc.)

**Subject:** ⚠️ TradeGo Alert: Circuit Breaker

**Content:**
```
Circuit Breaker

Daily loss limit of 2% reached. Trading paused.
```

---

## 🔧 Troubleshooting

### Problem: Email not sending

**Check 1:** Gmail App Password correct?
```python
# Test SMTP connection
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('your-email@gmail.com', 'your-app-password')
print("✅ SMTP login successful!")
```

**Check 2:** Less secure app access?
- Go to: https://myaccount.google.com/lesssecureapps
- Turn ON (if available)
- **Better:** Use App Password instead

**Check 3:** Firewall blocking port 587?
```bash
# Test if port is open
telnet smtp.gmail.com 587
```

### Problem: Callback server not receiving code

**Check 1:** Firewall allows port 8000?
```bash
# Ubuntu
sudo ufw allow 8000/tcp

# Check if server is running
netstat -tuln | grep 8000
```

**Check 2:** Redirect URI matches exactly?
- Upstox Developer Portal: `http://your-vps-ip:8000/callback`
- config.py: `UPSTOX_REDIRECT_URI = 'http://your-vps-ip:8000/callback'`
- **Must match EXACTLY** (including http/https, port, trailing slash)

**Check 3:** Can you access callback server?
```bash
# Test from browser
http://your-vps-ip:8000/status

# Should return:
{"token_valid": false, "token_expiry": null}
```

### Problem: Token expires too soon

**Solution:** Upstox tokens are valid for 24 hours. The system checks at 8:50 AM daily. This is normal behavior.

---

## 🎯 Daily Workflow (After Setup)

### What Happens Automatically:

**8:50 AM:**
- System checks token validity
- If expired, sends you email

**9:00 AM:**
- You check email
- Click "Authorize TradeGo" button
- Login to Upstox
- Enter PIN
- Done! (takes 30 seconds)

**9:15 AM - 3:30 PM:**
- System trades automatically
- You can check logs anytime

**3:35 PM:**
- System sends daily P&L report email

**You only spend 30 seconds per day clicking the email link!** ✅

---

## 🔒 Security Best Practices

1. **Never commit credentials to Git:**
   ```bash
   # Add to .gitignore
   echo "config.py" >> .gitignore
   echo ".env" >> .gitignore
   echo "data/*.json" >> .gitignore
   ```

2. **Use environment variables on VPS**
   - Don't hardcode in config.py
   - Set in systemd service file

3. **Use Gmail App Password**
   - Never use your actual Gmail password
   - Generate unique app password for TradeGo

4. **Secure callback server**
   - Runs only on localhost or VPS IP
   - No public internet exposure needed

---

## 📞 Need Help?

**Check logs first:**
```bash
# View email logs
grep "Email" ./data/tradego.log

# View token logs
grep "Token" ./data/tradego.log

# View errors
grep "ERROR" ./data/tradego.log
```

**Test individual components:**
```bash
python email_notifier.py  # Test email
python token_manager.py   # Test token refresh
```

---

## ✅ Setup Complete Checklist

- [ ] Upstox Developer App created
- [ ] API Key and Secret copied
- [ ] Redirect URI configured
- [ ] Gmail 2FA enabled
- [ ] Gmail App Password generated
- [ ] `config.py` updated with credentials
- [ ] Email test passed (`python email_notifier.py`)
- [ ] Token test passed (`python token_manager.py`)
- [ ] Received test email successfully
- [ ] Callback server accessible
- [ ] Full system test passed (`python orchestrator.py`)

**Once all checkboxes are ✅, you're ready to go!** 🚀

---

**That's it bro! Now you just click ONE email link every morning and the system handles everything else!**
