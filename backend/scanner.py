import random
import requests
import yfinance as yf

from database import SessionLocal
from models import Alert

from strategy import (
    calculate_price_change,
    calculate_spread,
    calculate_liquidity,
    calculate_atm
)

# =========================
# NSE SESSION CONFIG
# =========================

session = requests.Session()

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br"
}

# =========================
# INDIAN STOCKS
# =========================

STOCKS = [
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    "LT.NS",
    "ITC.NS",
    "AXISBANK.NS",
    "BHARTIARTL.NS",
    "KOTAKBANK.NS",
    "ASIANPAINT.NS",
    "MARUTI.NS",
    "SUNPHARMA.NS",
    "TITAN.NS",
    "ULTRACEMCO.NS",
    "BAJFINANCE.NS",
    "WIPRO.NS",
    "NTPC.NS",
    "POWERGRID.NS"
]

# =========================
# TRIGGERS
# =========================

DEFAULT_PRICE_TRIGGER = 2.0
DEFAULT_SPREAD_TRIGGER = 0.5
DEFAULT_ATM_TRIGGER = 4.0

# =========================
# SAVE ALERT
# =========================

def _save_alert(alert_data):

    db = SessionLocal()

    try:

        db_alert = Alert(
            stock=alert_data["stock"],
            price=alert_data["price"],
            change_percent=alert_data["change_percent"],
            spread=alert_data["spread"],
            liquidity=alert_data["liquidity"],
            atm_premium=alert_data["atm_premium"],
            atm=alert_data["atm"],
            signal=alert_data["signal"]
        )

        db.add(db_alert)
        db.commit()

    finally:
        db.close()

# =========================
# NSE OPTION CHAIN
# =========================

def fetch_nse_option_chain(symbol="NIFTY"):

    url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"

    # Get cookies first
    session.get(
        "https://www.nseindia.com",
        headers=HEADERS
    )

    response = session.get(
        url,
        headers=HEADERS
    )

    return response.json()

# =========================
# GET ATM OPTION
# =========================

def get_atm_option_data(option_chain, current_price):

    records = option_chain["records"]["data"]

    closest = min(
        records,
        key=lambda x: abs(x["strikePrice"] - current_price)
    )

    ce = closest.get("CE", {})

    bid = ce.get("bidprice", 0)
    ask = ce.get("askPrice", 0)

    if bid == 0:
        bid = random.uniform(5, 50)

    if ask == 0:
        ask = bid + random.uniform(1, 5)

    return {
        "bid": bid,
        "ask": ask,
        "strike": closest["strikePrice"],
        "oi": ce.get("openInterest", 0),
        "volume": ce.get("totalTradedVolume", 0)
    }

# =========================
# BUILD RESULT
# =========================

def _build_scan_result(
    symbol,
    current_price,
    previous_close,
    bid,
    ask,
    price_trigger,
    spread_trigger,
    atm_trigger
):

    current_price = float(current_price)
    previous_close = float(previous_close)
    bid = float(bid)
    ask = float(ask)

    price_change = calculate_price_change(
        current_price,
        previous_close
    )

    spread = calculate_spread(
        bid,
        ask,
        current_price
    )

    liquidity = calculate_liquidity(
        bid,
        ask,
        current_price
    )

    atm_premium = (bid + ask) / 2

    price_triggered = abs(price_change) >= price_trigger

    liquidity_alert = spread <= spread_trigger

    atm_alert = atm_premium >= atm_trigger

    signal = (
        "BUY ATM"
        if price_triggered and liquidity_alert and atm_alert
        else "NO ALERT"
    )

    reasons = []

    if not price_triggered:
        reasons.append("Price move below trigger")

    if not liquidity_alert:
        reasons.append("Spread too wide")

    if not atm_alert:
        reasons.append("ATM premium below trigger")

    return {
        "stock": symbol,
        "price": round(current_price, 2),
        "change_percent": round(price_change, 2),
        "spread": round(spread, 2),
        "liquidity": round(liquidity, 2),
        "atm_premium": round(atm_premium, 2),
        "atm": calculate_atm(current_price),
        "bid": round(bid, 2),
        "ask": round(ask, 2),
        "price_triggered": price_triggered,
        "liquidity_alert": liquidity_alert,
        "atm_alert": atm_alert,
        "signal": signal,
        "reason": ", ".join(reasons)
        if reasons
        else "All filters passed"
    }

# =========================
# MAIN SCANNER
# =========================

def run_scanner(
    price_trigger=DEFAULT_PRICE_TRIGGER,
    spread_trigger=DEFAULT_SPREAD_TRIGGER,
    atm_trigger=DEFAULT_ATM_TRIGGER
):

    results = []

    try:
        option_chain = fetch_nse_option_chain("NIFTY")
    except Exception as e:
        print("NSE Option Chain Error:", e)
        option_chain = None

    for symbol in STOCKS:

        try:

            ticker = yf.Ticker(symbol)

            hist = ticker.history(period="5d")

            if len(hist) < 2:

                results.append({
                    "stock": symbol,
                    "signal": "NO DATA",
                    "reason": "Not enough price history"
                })

                continue

            previous_close = hist["Close"].iloc[-2]

            current_price = hist["Close"].iloc[-1]

            # OPTION DATA
            if option_chain:

                option_data = get_atm_option_data(
                    option_chain,
                    current_price
                )

                bid = option_data["bid"]
                ask = option_data["ask"]

            else:

                bid = current_price - random.uniform(1, 5)
                ask = current_price + random.uniform(1, 5)

            scan_result = _build_scan_result(
                symbol,
                current_price,
                previous_close,
                bid,
                ask,
                price_trigger,
                spread_trigger,
                atm_trigger
            )

            results.append(scan_result)

            if scan_result["signal"] == "BUY ATM":
                _save_alert(scan_result)

        except Exception as e:

            print(symbol, e)

            results.append({
                "stock": symbol,
                "signal": "NO DATA",
                "reason": str(e)
            })

    return results