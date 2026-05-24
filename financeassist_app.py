# =============================================================
# financeassist_app.py -- FinanceAssist AI FastAPI Application
# A finance-domain agentic AI app exposed via ngrok
# =============================================================

import os
import time
import json
import logging
from dotenv import load_dotenv

# Load .env before any other module reads environment variables
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
# JSON logs are parseable by Datadog, CloudWatch, GCP Logging.
# Never use print() for production logging.
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
# In production replace these with real APIs (bank APIs,
# stock market APIs like Alpha Vantage, portfolio DBs, etc.)
# =============================================================

@tool
def get_stock_price(symbol: str) -> str:
    """Get the current stock price and daily change for a given ticker symbol."""
    mock_stocks = {
        "RELIANCE": {"price": 2847.50, "change": +1.2, "high": 2870.00, "low": 2810.30, "volume": "12.4M"},
        "TCS":      {"price": 3965.80, "change": -0.8, "high": 4010.00, "low": 3940.50, "volume": "5.6M"},
        "INFY":     {"price": 1580.25, "change": +2.1, "high": 1595.00, "low": 1555.00, "volume": "8.9M"},
        "HDFCBANK": {"price": 1645.90, "change": +0.5, "high": 1660.00, "low": 1630.20, "volume": "7.2M"},
        "WIPRO":    {"price": 465.30,  "change": -1.5, "high": 478.00,  "low": 460.10,  "volume": "10.1M"},
        "SBIN":     {"price": 825.60,  "change": +0.9, "high": 835.00,  "low": 818.40,  "volume": "15.3M"},
        "ICICIBANK":{"price": 1245.70, "change": +1.8, "high": 1260.00, "low": 1230.00, "volume": "6.8M"},
        "TATAMOTORS":{"price": 985.40, "change": -2.3, "high": 1010.00, "low": 978.50, "volume": "9.5M"},
    }
    sym = symbol.strip().upper()
    data = mock_stocks.get(sym)
    if data:
        direction = "▲" if data["change"] >= 0 else "▼"
        return (
            f"{sym}: ₹{data['price']:,.2f} ({direction} {abs(data['change'])}%) | "
            f"High: ₹{data['high']:,.2f} | Low: ₹{data['low']:,.2f} | Vol: {data['volume']}"
        )
    available = ", ".join(mock_stocks.keys())
    return f"Symbol '{sym}' not found. Available: {available}"


@tool
def get_mutual_fund_info(fund_name: str) -> str:
    """Get NAV, returns, and category details for a mutual fund."""
    mock_funds = {
        "axis bluechip":     {"nav": 52.34, "1yr": 18.5, "3yr": 14.2, "category": "Large Cap", "risk": "Moderate"},
        "mirae asset large": {"nav": 98.76, "1yr": 22.1, "3yr": 16.8, "category": "Large Cap", "risk": "Moderate"},
        "parag parikh flexi":{"nav": 72.10, "1yr": 25.3, "3yr": 19.5, "category": "Flexi Cap", "risk": "Moderate-High"},
        "sbi small cap":     {"nav": 145.60,"1yr": 32.7, "3yr": 24.1, "category": "Small Cap", "risk": "High"},
        "hdfc mid cap":      {"nav": 115.20,"1yr": 28.4, "3yr": 20.6, "category": "Mid Cap",   "risk": "High"},
        "icici pru balanced": {"nav": 62.85, "1yr": 15.2, "3yr": 12.8, "category": "Hybrid",   "risk": "Low-Moderate"},
    }
    query = fund_name.strip().lower()
    for key, data in mock_funds.items():
        if key in query or any(word in query for word in key.split()):
            return (
                f"{key.title()} Fund | NAV: ₹{data['nav']} | "
                f"1Y Return: {data['1yr']}% | 3Y Return: {data['3yr']}% | "
                f"Category: {data['category']} | Risk: {data['risk']}"
            )
    available = ", ".join(k.title() for k in mock_funds.keys())
    return f"No match for '{fund_name}'. Available funds: {available}"


@tool
def get_account_summary(account_id: str) -> str:
    """Get account balance, recent transactions, and account type for a customer."""
    mock_accounts = {
        "ACC001": {
            "name": "Rahul Sharma", "type": "Savings",
            "balance": 245000.50, "currency": "INR",
            "recent_txns": [
                {"date": "2026-03-20", "desc": "UPI - Swiggy", "amount": -450.00},
                {"date": "2026-03-19", "desc": "Salary Credit", "amount": +85000.00},
                {"date": "2026-03-18", "desc": "EMI - Home Loan", "amount": -32500.00},
            ]
        },
        "ACC002": {
            "name": "Priya Patel", "type": "Current",
            "balance": 1250000.00, "currency": "INR",
            "recent_txns": [
                {"date": "2026-03-20", "desc": "NEFT - Vendor Payment", "amount": -150000.00},
                {"date": "2026-03-19", "desc": "Client Invoice", "amount": +320000.00},
                {"date": "2026-03-17", "desc": "GST Payment", "amount": -45000.00},
            ]
        },
        "ACC003": {
            "name": "Amit Kumar", "type": "Savings",
            "balance": 78500.75, "currency": "INR",
            "recent_txns": [
                {"date": "2026-03-20", "desc": "ATM Withdrawal", "amount": -5000.00},
                {"date": "2026-03-18", "desc": "SIP - Axis Bluechip", "amount": -5000.00},
                {"date": "2026-03-15", "desc": "Freelance Payment", "amount": +25000.00},
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
            f"Account: {acc} ({data['type']}) | Holder: {data['name']}\n"
            f"Balance: ₹{data['balance']:,.2f}\n"
            f"Recent Transactions:\n{txn_lines}"
        )
    return f"Account '{acc}' not found. Try ACC001, ACC002, or ACC003."


@tool
def calculate_emi(principal: float, annual_rate: float, tenure_months: int) -> str:
    """Calculate EMI (Equated Monthly Installment) for a loan.
    Args: principal (loan amount in INR), annual_rate (interest % per year), tenure_months (loan duration)."""
    if principal <= 0 or annual_rate <= 0 or tenure_months <= 0:
        return "All values must be positive. Please provide valid principal, rate, and tenure."

    monthly_rate = annual_rate / (12 * 100)
    emi = principal * monthly_rate * ((1 + monthly_rate) ** tenure_months) / (((1 + monthly_rate) ** tenure_months) - 1)
    total_payment = emi * tenure_months
    total_interest = total_payment - principal

    return (
        f"Loan: ₹{principal:,.2f} | Rate: {annual_rate}% p.a. | Tenure: {tenure_months} months\n"
        f"Monthly EMI: ₹{emi:,.2f}\n"
        f"Total Interest: ₹{total_interest:,.2f}\n"
        f"Total Payment: ₹{total_payment:,.2f}"
    )


# =============================================================
# Agent Setup
# =============================================================

SYSTEM_PROMPT = (
    "You are FinanceAssist, a professional financial advisor AI for WealthEasy,\n"
    "an Indian fintech platform.\n\n"
    "Your capabilities:\n"
    "- Check stock prices using the get_stock_price tool\n"
    "- Provide mutual fund information using get_mutual_fund_info\n"
    "- Show account summaries using get_account_summary\n"
    "- Calculate loan EMIs using calculate_emi\n"
    "- Answer general queries about personal finance, investing basics,\n"
    "  tax-saving instruments (ELSS, PPF, NPS), and financial planning\n\n"
    "Your boundaries:\n"
    "- Never give specific buy/sell recommendations -- always say\n"
    "  'consult a SEBI-registered advisor'\n"
    "- Do not discuss non-finance topics\n"
    "- If you cannot help, direct the customer to call 1800-WEALTHEASY\n"
    "- Always respond in the same language the customer uses\n"
    "- Be concise, professional, and helpful\n"
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
    description="LangGraph-powered financial advisor agent for WealthEasy.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================
# Pydantic Schemas
# =============================================================

class ChatRequest(BaseModel):
    session_id: str = Field(
        ...,
        description="Unique session identifier per customer.",
        examples=["customer_12345"],
    )
    message: str = Field(
        ...,
        description="The customer query.",
        examples=["What is the price of RELIANCE stock?"],
    )


class ChatResponse(BaseModel):
    session_id: str
    response: str
    latency_ms: float


class HealthResponse(BaseModel):
    status: str
    uptime_seconds: float
    model: str
    tools_available: list


SERVER_START_TIME = time.time()


# =============================================================
# Endpoints
# =============================================================

@app.get("/health", response_model=HealthResponse, tags=["Operations"])
def health_check():
    """Health check endpoint for load balancers and monitoring."""
    return HealthResponse(
        status="healthy",
        uptime_seconds=round(time.time() - SERVER_START_TIME, 2),
        model="gpt-4o-mini",
        tools_available=[
            "get_stock_price",
            "get_mutual_fund_info",
            "get_account_summary",
            "calculate_emi",
        ],
    )


@app.post("/chat", response_model=ChatResponse, tags=["Agent"])
def chat(request: ChatRequest):
    """
    Main chat endpoint. Pass the same session_id across turns
    to maintain conversation context within a session.
    """
    logger.info(
        "Incoming request",
        extra={"session_id": request.session_id, "message_length": len(request.message)},
    )
    start_time = time.time()
    try:
        config = {"configurable": {"thread_id": request.session_id}}
        result = agent.invoke(
            {"messages": [HumanMessage(content=request.message)]},
            config=config,
        )
        response_text = result["messages"][-1].content
        latency_ms = round((time.time() - start_time) * 1000, 2)

        logger.info(
            "Request completed",
            extra={"session_id": request.session_id, "latency_ms": latency_ms},
        )
        return ChatResponse(
            session_id=request.session_id,
            response=response_text,
            latency_ms=latency_ms,
        )
    except Exception as e:
        logger.error(
            "Agent invocation failed",
            extra={"session_id": request.session_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=500,
            detail="FinanceAssist is temporarily unavailable. Please try again shortly.",
        )
