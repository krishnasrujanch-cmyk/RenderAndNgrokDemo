# =============================================================
# financeassist_app.py -- FinanceAssist AI FastAPI Application
# Real stock prices via Yahoo Finance (yfinance) -- free, no API key needed
# =============================================================

import os
import time
import json
import logging
import requests as http_requests
from dotenv import load_dotenv

load_dotenv(override=True)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver


# =============================================================
# Structured JSON Logger
# =============================================================

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in logging.LogRecord.__dict__ and key not in log_entry:
                log_entry[key] = value
        return json.dumps(log_entry)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


logger = get_logger("financeassist")


# =============================================================
# Tools -- Finance Domain
# =============================================================

@tool
def get_stock_price(symbol: str) -> str:
    """Get the real-time stock price for ANY stock ticker using Yahoo Finance.
    For Indian stocks add .NS suffix (e.g. RELIANCE.NS, TCS.NS, INFY.NS).
    For US stocks use the ticker directly (e.g. AAPL, TSLA, GOOGL, GEV).
    The agent should automatically append .NS for Indian company names.
    """
    import yfinance as yf

    sym = symbol.strip().upper()

    # Auto-add .NS for known Indian stocks if no exchange suffix provided
    indian_keywords = [
        "RELIANCE", "TCS", "INFY", "WIPRO", "HDFCBANK", "SBIN", "ICICIBANK",
        "TATAMOTORS", "HINDUNILVR", "BAJFINANCE", "KOTAKBANK", "AXISBANK",
        "MARUTI", "SUNPHARMA", "LTIM", "TECHM", "ULTRACEMCO", "TITAN",
        "ASIANPAINT", "NESTLEIND", "POWERGRID", "NTPC", "ONGC", "COALINDIA",
    ]
    if "." not in sym and sym in indian_keywords:
        sym = sym + ".NS"

    try:
        ticker = yf.Ticker(sym)
        info = ticker.info

        # yfinance returns empty dict for invalid symbols
        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
        if not current_price:
            return (
                f"Could not fetch price for '{symbol}'. "
                f"For Indian stocks use NSE symbol + .NS (e.g. RELIANCE.NS). "
                f"For US stocks use the ticker directly (e.g. AAPL, GEV, TSLA)."
            )

        name        = info.get("longName") or info.get("shortName") or sym
        currency    = info.get("currency", "")
        prev_close  = info.get("previousClose", current_price)
        change_pct  = ((current_price - prev_close) / prev_close * 100) if prev_close else 0
        day_high    = info.get("dayHigh", "N/A")
        day_low     = info.get("dayLow", "N/A")
        volume      = info.get("volume", "N/A")
        market_cap  = info.get("marketCap")
        direction   = "▲" if change_pct >= 0 else "▼"

        result = (
            f"{name} ({sym})\n"
            f"Price     : {currency} {current_price:,.2f} ({direction} {abs(change_pct):.2f}%)\n"
            f"Day High  : {currency} {day_high}\n"
            f"Day Low   : {currency} {day_low}\n"
            f"Volume    : {volume:,}" if isinstance(volume, int) else
            f"Volume    : {volume}"
        )
        if market_cap:
            result += f"\nMarket Cap: {currency} {market_cap:,}"

        return result

    except Exception as e:
        return f"Error fetching data for '{symbol}': {str(e)}. Please verify the ticker symbol."


@tool
def get_mutual_fund_info(fund_name: str) -> str:
    """Get NAV, returns, and category details for Indian mutual funds via MFAPI."""
    # Search for fund using MFAPI (free, no key needed)
    try:
        search_url = f"https://api.mfapi.in/mf/search?q={fund_name}"
        resp = http_requests.get(search_url, timeout=8)
        results = resp.json()

        if not results:
            return f"No mutual fund found matching '{fund_name}'. Try searching with fund house name e.g. 'SBI Small Cap' or 'Axis Bluechip'."

        # Take top result
        fund = results[0]
        scheme_code = fund.get("schemeCode")
        scheme_name = fund.get("schemeName", "Unknown")

        # Get NAV details
        nav_url = f"https://api.mfapi.in/mf/{scheme_code}"
        nav_resp = http_requests.get(nav_url, timeout=8)
        nav_data = nav_resp.json()

        meta = nav_data.get("meta", {})
        nav_history = nav_data.get("data", [])

        current_nav = nav_history[0]["nav"] if nav_history else "N/A"
        nav_date    = nav_history[0]["date"] if nav_history else "N/A"

        # Calculate 1-year return if enough history
        returns_str = ""
        if len(nav_history) >= 252:
            old_nav = float(nav_history[251]["nav"])
            new_nav = float(nav_history[0]["nav"])
            one_yr_return = ((new_nav - old_nav) / old_nav) * 100
            returns_str = f"\n1Y Return : {one_yr_return:.2f}%"

        return (
            f"{scheme_name}\n"
            f"NAV       : ₹{current_nav} (as of {nav_date})"
            f"{returns_str}\n"
            f"Fund House: {meta.get('fund_house', 'N/A')}\n"
            f"Category  : {meta.get('scheme_category', 'N/A')}\n"
            f"Type      : {meta.get('scheme_type', 'N/A')}"
        )

    except Exception as e:
        return f"Error fetching mutual fund data: {str(e)}. Try again with a more specific fund name."


@tool
def get_account_summary(account_id: str) -> str:
    """Get account balance, recent transactions, and account type for a customer."""
    mock_accounts = {
        "ACC001": {
            "name": "Rahul Sharma", "type": "Savings",
            "balance": 245000.50,
            "recent_txns": [
                {"date": "2026-03-20", "desc": "UPI - Swiggy",     "amount": -450.00},
                {"date": "2026-03-19", "desc": "Salary Credit",    "amount": +85000.00},
                {"date": "2026-03-18", "desc": "EMI - Home Loan",  "amount": -32500.00},
            ]
        },
        "ACC002": {
            "name": "Priya Patel", "type": "Current",
            "balance": 1250000.00,
            "recent_txns": [
                {"date": "2026-03-20", "desc": "NEFT - Vendor",    "amount": -150000.00},
                {"date": "2026-03-19", "desc": "Client Invoice",   "amount": +320000.00},
                {"date": "2026-03-17", "desc": "GST Payment",      "amount": -45000.00},
            ]
        },
        "ACC003": {
            "name": "Amit Kumar", "type": "Savings",
            "balance": 78500.75,
            "recent_txns": [
                {"date": "2026-03-20", "desc": "ATM Withdrawal",   "amount": -5000.00},
                {"date": "2026-03-18", "desc": "SIP - Axis Blue",  "amount": -5000.00},
                {"date": "2026-03-15", "desc": "Freelance Payment","amount": +25000.00},
            ]
        },
    }
    acc = account_id.strip().upper()
    data = mock_accounts.get(acc)
    if data:
        txn_lines = "\n".join(
            f"  {t['date']} | {t['desc']} | {'+'if t['amount']>0 else ''}₹{abs(t['amount']):,.2f}"
            for t in data["recent_txns"]
        )
        return (
            f"Account : {acc} ({data['type']}) | Holder: {data['name']}\n"
            f"Balance : ₹{data['balance']:,.2f}\n"
            f"Recent Transactions:\n{txn_lines}"
        )
    return f"Account '{acc}' not found. Try ACC001, ACC002, or ACC003."


@tool
def calculate_emi(principal: float, annual_rate: float, tenure_months: int) -> str:
    """Calculate EMI for a loan.
    Args: principal (INR), annual_rate (% per year), tenure_months."""
    if principal <= 0 or annual_rate <= 0 or tenure_months <= 0:
        return "All values must be positive."

    r = annual_rate / (12 * 100)
    emi = principal * r * ((1 + r) ** tenure_months) / (((1 + r) ** tenure_months) - 1)
    total   = emi * tenure_months
    interest = total - principal

    return (
        f"Loan      : ₹{principal:,.2f} @ {annual_rate}% p.a. for {tenure_months} months\n"
        f"Monthly EMI   : ₹{emi:,.2f}\n"
        f"Total Interest: ₹{interest:,.2f}\n"
        f"Total Payment : ₹{total:,.2f}"
    )


# =============================================================
# Agent Setup
# =============================================================

SYSTEM_PROMPT = (
    "You are FinanceAssist, a professional financial advisor AI for WealthEasy,\n"
    "an Indian fintech platform.\n\n"
    "Your capabilities:\n"
    "- Check REAL-TIME stock prices using get_stock_price tool\n"
    "  * For Indian stocks: use NSE symbol + .NS (e.g. RELIANCE.NS, TCS.NS)\n"
    "  * For US stocks: use ticker directly (e.g. AAPL, TSLA, GEV, GOOGL)\n"
    "  * Always try to resolve company names to their ticker symbol\n"
    "- Get REAL mutual fund NAV using get_mutual_fund_info\n"
    "- Show account summaries using get_account_summary\n"
    "- Calculate loan EMIs using calculate_emi\n"
    "- Answer general queries about personal finance, investing,\n"
    "  tax-saving (ELSS, PPF, NPS), and financial planning\n\n"
    "Your boundaries:\n"
    "- Never give specific buy/sell recommendations\n"
    "- Always say 'consult a SEBI-registered advisor' for investment decisions\n"
    "- Do not discuss non-finance topics\n"
    "- If you cannot help, direct to 1800-WEALTHEASY\n"
    "- Respond in the same language the customer uses\n"
    "- Use ₹ for Indian Rupee amounts"
)

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY"),
    openai_api_base=os.getenv("OPENAI_BASE_URL")
)

memory = MemorySaver()

agent = create_react_agent(
    model=llm,
    tools=[get_stock_price, get_mutual_fund_info, get_account_summary, calculate_emi],
    checkpointer=memory,
    prompt=SYSTEM_PROMPT,
)

logger.info("FinanceAssist agent initialised", extra={"model": "gpt-4o-mini", "tools": 4})


# =============================================================
# FastAPI Application
# =============================================================

app = FastAPI(
    title="FinanceAssist AI",
    description="LangGraph-powered financial advisor with real-time stock & mutual fund data.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    session_id: str = Field(..., examples=["customer_12345"])
    message: str    = Field(..., examples=["What is the price of RELIANCE stock?"])


class ChatResponse(BaseModel):
    session_id: str
    response: str
    latency_ms: float


class HealthResponse(BaseModel):
    status: str
    uptime_seconds: float
    model: str
    tools_available: list
    data_sources: list


SERVER_START_TIME = time.time()


@app.get("/health", response_model=HealthResponse, tags=["Operations"])
def health_check():
    return HealthResponse(
        status="healthy",
        uptime_seconds=round(time.time() - SERVER_START_TIME, 2),
        model="gpt-4o-mini",
        tools_available=["get_stock_price", "get_mutual_fund_info", "get_account_summary", "calculate_emi"],
        data_sources=["Yahoo Finance (real-time)", "MFAPI.in (real NAV)", "Mock accounts"],
    )


@app.post("/chat", response_model=ChatResponse, tags=["Agent"])
def chat(request: ChatRequest):
    logger.info("Incoming request", extra={"session_id": request.session_id, "message_length": len(request.message)})
    start_time = time.time()
    try:
        config = {"configurable": {"thread_id": request.session_id}}
        result = agent.invoke(
            {"messages": [HumanMessage(content=request.message)]},
            config=config,
        )
        response_text = result["messages"][-1].content
        latency_ms = round((time.time() - start_time) * 1000, 2)
        logger.info("Request completed", extra={"session_id": request.session_id, "latency_ms": latency_ms})
        return ChatResponse(session_id=request.session_id, response=response_text, latency_ms=latency_ms)
    except Exception as e:
        logger.error("Agent invocation failed", extra={"session_id": request.session_id, "error": str(e)})
        raise HTTPException(status_code=500, detail="FinanceAssist is temporarily unavailable.")