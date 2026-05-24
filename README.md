# FinanceAssist AI — Agentic Finance Chatbot with ngrok

A **LangGraph-powered financial advisor agent** exposed to the internet via **ngrok**.
Built with FastAPI, OpenAI (gpt-4o-mini), and LangGraph's ReAct agent pattern.

---

## What is ngrok?

ngrok creates a secure tunnel from a public URL to your local machine.
You run a server on `localhost:8000` and instantly share it with anyone on the internet —
no cloud deployment needed.

```
[Internet User]
      │
      ▼
[https://abc123.ngrok-free.app]   ← ngrok public URL (HTTPS)
      │  encrypted tunnel
      ▼
[ngrok agent on your laptop]
      │
      ▼
[localhost:8000]                  ← your FastAPI app
```

**Common use cases:**
- Demo your API to teammates without deploying
- Test webhooks (Stripe, Razorpay, GitHub) that need a public URL
- Let a mobile app hit your local backend during development
- Share a prototype with a client in 30 seconds

---

## Project Structure

```
financeassist/
├── financeassist_app.py   # FastAPI app + LangGraph agent + 4 finance tools
├── run_with_ngrok.py      # Starts FastAPI server + reads ngrok tunnel URL
├── test_api.py            # Test script for all endpoints
├── requirements.txt       # Python dependencies
├── .env.example           # Template for environment variables
├── .gitignore             # Excludes .env and __pycache__
└── README.md              # This file
```

---

## Available Finance Tools

| Tool | Description | Example Query |
|------|-------------|---------------|
| `get_stock_price` | Current price, change%, high/low | "Price of RELIANCE" |
| `get_mutual_fund_info` | NAV, returns, risk category | "Tell me about SBI Small Cap" |
| `get_account_summary` | Balance + recent transactions | "Show account ACC001" |
| `calculate_emi` | Loan EMI calculation | "EMI for 50L at 8.5% for 20 years" |

---

## Setup Guide

### Step 1: Get Your API Keys

**OpenAI API Key:**
1. Go to https://platform.openai.com/api-keys
2. Create a new secret key and copy it

**ngrok Auth Token:**
1. Sign up free at https://ngrok.com
2. Go to https://dashboard.ngrok.com/get-started/your-authtoken
3. Copy your authtoken

### Step 2: Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate        # Mac/Linux
# venv\Scripts\activate         # Windows
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt --upgrade
```

> **Note:** Use `--upgrade` to resolve any existing langchain version conflicts
> in your environment.

### Step 4: Create .env File

```bash
cp .env.example .env
```

Edit `.env`:
```env
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxx
```

### Step 5: Install ngrok (Real Binary via Homebrew)

```bash
brew install ngrok/ngrok/ngrok
ngrok config add-authtoken YOUR_NGROK_AUTH_TOKEN
```

> **Critical:** Do NOT use `pip install pyngrok` for running ngrok.
> pyngrok places a fake `ngrok` script in your PATH that causes SSL errors.
> Always install the real binary via Homebrew.

### Step 6: Start the FastAPI Server

**Terminal 1:**
```bash
uvicorn financeassist_app:app --host 0.0.0.0 --port 8000
```

Wait until you see:
```
Application startup complete.
Uvicorn running on http://0.0.0.0:8000
```

### Step 7: Start ngrok Tunnel

**Terminal 2** (while on mobile hotspot if on ACT Fibernet — see issues below):
```bash
ngrok http 8000
```

You'll see:
```
Session Status    online
Forwarding        https://abc-xyz.ngrok-free.dev -> http://localhost:8000
```

### Step 8: Test It

```bash
# Health check
curl https://YOUR-URL.ngrok-free.dev/health

# Full test suite
python test_api.py https://YOUR-URL.ngrok-free.dev

# Swagger UI (in browser)
https://YOUR-URL.ngrok-free.dev/docs
```

---

## API Endpoints

### GET /health
```bash
curl https://your-ngrok-url.ngrok-free.dev/health
```
```json
{
  "status": "healthy",
  "uptime_seconds": 24.5,
  "model": "gpt-4o-mini",
  "tools_available": ["get_stock_price", "get_mutual_fund_info", "get_account_summary", "calculate_emi"]
}
```

### POST /chat
```bash
curl -X POST https://your-ngrok-url.ngrok-free.dev/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "user_001", "message": "What is the price of TCS stock?"}'
```
```json
{
  "session_id": "user_001",
  "response": "TCS is currently trading at ₹3,965.80...",
  "latency_ms": 1234.56
}
```

---

## Issues We Faced & How We Fixed Them

### Issue 1: langchain-core version conflict
**Error:**
```
Cannot install langchain-core==0.3.0 because langchain-openai 0.3.0
requires langchain-core>=0.3.29
```
**Fix:** Use flexible version ranges in requirements.txt:
```
langchain-core>=0.3.29
langchain>=0.3.0
langchain-community>=0.3.0
```
And always install with:
```bash
pip install -r requirements.txt --upgrade
```

---

### Issue 2: pyngrok SSL Certificate Error
**Error:**
```
ssl.SSLCertVerificationError: certificate verify failed:
unable to get local issuer certificate
pyngrok.exception.PyngrokNgrokInstallError
```
**Root Cause:** pyngrok tries to download the ngrok binary over HTTPS but
Homebrew Python on macOS doesn't trust system certificates.

**Fix:** Never use pyngrok to run ngrok. Install the real binary:
```bash
brew install ngrok/ngrok/ngrok
```

---

### Issue 3: Fake ngrok binary from pyngrok in PATH
**Error:** Even after installing ngrok via Homebrew, running `ngrok` still
triggered pyngrok and threw SSL errors.

**Diagnosis:**
```bash
which ngrok
# /Users/srujan/shared_envs/ml_env/bin/ngrok  ← pyngrok's fake script!
```

**Fix:** Remove pyngrok's fake binary from your virtualenv:
```bash
rm /Users/srujan/shared_envs/ml_env/bin/ngrok

# Verify real binary is now used
which ngrok
# /opt/homebrew/bin/ngrok ✅

ngrok version
# ngrok version 3.x.x ✅ (no Python traceback)
```

---

### Issue 4: Port 8000 already in use
**Error:**
```
ERROR: [Errno 48] error while attempting to bind on address
('0.0.0.0', 8000): address already in use
```
**Fix:**
```bash
lsof -ti:8000 | xargs kill -9
pkill -f ngrok
```

---

### Issue 5: ngrok tunnel list empty / "list index out of range"
**Error:** ngrok process started but no tunnels were visible at
`http://127.0.0.1:4040/api/tunnels`

**Root Cause:** The script read the tunnel API before ngrok had time to
establish the tunnel (race condition).

**Fix:** Add a retry loop — poll the API every 2 seconds for up to 20 seconds
until tunnels appear.

---

### Issue 6: ngrok "failed to fetch CRL" — ACT Fibernet blocking
**Error:**
```
Session Status: reconnecting (failed to send authentication request:
failed to fetch CRL. errors encountered: timeout)
```
**Diagnosis:**
```bash
curl -v http://crl.ngrok-agent.com/ngrok.crl
# Response: 302 redirect to http://portalv6test.actcorp.in
```
ACT Fibernet intercepts HTTP requests and redirects them to a captive portal,
breaking ngrok's Certificate Revocation List (CRL) check.

**Fix:** Use mobile hotspot (iPhone/Android) instead of ACT Fibernet WiFi.
ngrok works perfectly on mobile data.

**Alternative fix (on ACT WiFi):** Change DNS to Google:
```bash
sudo networksetup -setdnsservers Wi-Fi 8.8.8.8 8.8.4.4
sudo dscacheutil -flushcache
```

---

### Issue 7: ngrok shows warning page before API response
**Symptom:** Clicking a ngrok URL in the browser shows an interstitial
warning page saying "You are about to visit...".

**Fix:** This is normal for free ngrok tunnels. Click "Visit Site" to proceed.
For API calls (curl/Postman), it doesn't appear — only in browsers.

---

## ngrok Tips

### Free Tier Limitations
- URL changes every restart (paid plans get a fixed subdomain)
- Sessions expire after ~2 hours of inactivity
- Rate-limited to 20 connections/minute

### ngrok Web Inspector
While ngrok is running, open **http://127.0.0.1:4040** to see:
- Every HTTP request and response in real-time
- Full headers, body, and timing
- Replay any request (great for debugging webhooks)

### Useful Commands
```bash
# Check ngrok version
ngrok version

# View config file
cat ~/Library/Application\ Support/ngrok/ngrok.yml

# Set auth token
ngrok config add-authtoken YOUR_TOKEN

# Run with debug logs
ngrok http 8000 --log=stdout --log-level=debug

# Run with specific region (helps on some networks)
ngrok http 8000 --region=in
```

---

## Architecture Overview

```
┌──────────────────────────────────────────────────┐
│                  FastAPI App                      │
│                                                   │
│  GET  /health ── status + uptime + tools          │
│                                                   │
│  POST /chat ──┬─► LangGraph ReAct Agent          │
│               │        │                          │
│               │        ├── get_stock_price()      │
│               │        ├── get_mutual_fund_info() │
│               │        ├── get_account_summary()  │
│               │        └── calculate_emi()        │
│               │                                   │
│               └─► MemorySaver (session memory)    │
│                                                   │
│  Logging ── Structured JSON → stdout              │
└─────────────────────┬────────────────────────────┘
                      │ localhost:8000
                      ▼
               ┌──────────────┐
               │  ngrok agent │
               └──────┬───────┘
                      │ encrypted tunnel
                      ▼
        https://xxx.ngrok-free.app
                      │
                      ▼
               [Public Internet]
```

---

## Running Locally (Without ngrok)

```bash
uvicorn financeassist_app:app --host 0.0.0.0 --port 8000 --reload
```

Open http://localhost:8000/docs for Swagger UI.

---

## Moving to Production

| Platform | Steps |
|----------|-------|
| **Render** | Push to GitHub → connect repo → auto-deploy |
| **Railway** | `railway up` |
| **Google Cloud Run** | Dockerize → `gcloud run deploy` |
| **AWS ECS** | Dockerize → push to ECR → create ECS service |

Replace mock tools with real APIs:
- Stock prices → Alpha Vantage, Yahoo Finance, NSE API
- Mutual funds → MFAPI.in, AMFI NAV data
- Accounts → Your bank's core banking API or database
- EMI → Already correct, keep as-is

---

## License

Educational project. Use and modify freely.