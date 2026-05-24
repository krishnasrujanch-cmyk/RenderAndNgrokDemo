# =============================================================
# test_api.py -- Test the FinanceAssist API
#
# Usage:
#   python test_api.py                           # test localhost
#   python test_api.py https://abc123.ngrok.io   # test ngrok URL
# =============================================================

import sys
import requests
import json

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
SESSION_ID = "test_session_001"


def separator(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def test_health():
    separator("TEST 1: Health Check")
    r = requests.get(f"{BASE_URL}/health")
    print(f"Status: {r.status_code}")
    print(json.dumps(r.json(), indent=2))
    assert r.status_code == 200
    print("✅ PASSED")


def test_stock_price():
    separator("TEST 2: Stock Price Query")
    r = requests.post(f"{BASE_URL}/chat", json={
        "session_id": SESSION_ID,
        "message": "What is the current price of RELIANCE?"
    })
    data = r.json()
    print(f"Response: {data['response']}")
    print(f"Latency : {data['latency_ms']}ms")
    assert r.status_code == 200
    print("✅ PASSED")


def test_mutual_fund():
    separator("TEST 3: Mutual Fund Info")
    r = requests.post(f"{BASE_URL}/chat", json={
        "session_id": SESSION_ID,
        "message": "Tell me about SBI Small Cap fund"
    })
    data = r.json()
    print(f"Response: {data['response']}")
    print(f"Latency : {data['latency_ms']}ms")
    assert r.status_code == 200
    print("✅ PASSED")


def test_account_summary():
    separator("TEST 4: Account Summary")
    r = requests.post(f"{BASE_URL}/chat", json={
        "session_id": SESSION_ID,
        "message": "Show me the account summary for ACC001"
    })
    data = r.json()
    print(f"Response: {data['response']}")
    print(f"Latency : {data['latency_ms']}ms")
    assert r.status_code == 200
    print("✅ PASSED")


def test_emi_calculator():
    separator("TEST 5: EMI Calculator")
    r = requests.post(f"{BASE_URL}/chat", json={
        "session_id": SESSION_ID,
        "message": "Calculate EMI for a home loan of 50 lakhs at 8.5% for 20 years"
    })
    data = r.json()
    print(f"Response: {data['response']}")
    print(f"Latency : {data['latency_ms']}ms")
    assert r.status_code == 200
    print("✅ PASSED")


def test_general_finance_query():
    separator("TEST 6: General Finance Query")
    r = requests.post(f"{BASE_URL}/chat", json={
        "session_id": SESSION_ID,
        "message": "What are the best tax-saving options under Section 80C?"
    })
    data = r.json()
    print(f"Response: {data['response']}")
    print(f"Latency : {data['latency_ms']}ms")
    assert r.status_code == 200
    print("✅ PASSED")


def test_boundary():
    separator("TEST 7: Out-of-Scope Query (Boundary Test)")
    r = requests.post(f"{BASE_URL}/chat", json={
        "session_id": SESSION_ID,
        "message": "What is the best pizza place nearby?"
    })
    data = r.json()
    print(f"Response: {data['response']}")
    assert r.status_code == 200
    print("✅ PASSED (agent should decline non-finance topics)")


if __name__ == "__main__":
    print(f"\n🔗 Testing against: {BASE_URL}\n")
    test_health()
    test_stock_price()
    test_mutual_fund()
    test_account_summary()
    test_emi_calculator()
    test_general_finance_query()
    test_boundary()
    print(f"\n{'='*60}")
    print("  🎉 ALL TESTS PASSED!")
    print(f"{'='*60}\n")
