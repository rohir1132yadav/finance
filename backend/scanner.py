import random
import os
from datetime import datetime, timedelta
import yfinance as yf

from strategy import (
    calculate_price_change,
    calculate_spread,
    calculate_liquidity,
    calculate_atm
)
from database import SessionLocal
from models import Alert

api_key = os.getenv("ALPACA_API_KEY")
secret = os.getenv("ALPACA_SECRET")
use_real = bool(api_key and secret)

if use_real:
    from alpaca.data import StockHistoricalDataClient, TimeFrame, OptionHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest, OptionChainRequest, OptionLatestQuoteRequest
    from alpaca.trading.enums import ContractType

    stock_client = StockHistoricalDataClient(api_key, secret)
    option_client = OptionHistoricalDataClient(api_key, secret)

STOCKS = [
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "NVDA",
    "TSLA",
    "META",
    "NFLX",
    "AMD",
    "INTC",
    "JPM",
    "BAC",
    "GS",
    "MS",
    "WFC",
    "PFE",
    "JNJ",
    "MRK",
    "ABBV",
    "BMY",
    "XOM",
    "CVX",
    "COP",
    "SLB",
    "ORCL",
    "CRM",
    "ADBE",
    "PYPL",
    "AVGO",
    "QCOM",
    "TXN",
    "AMAT",
    "INTU",
    "ISRG",
    "HON",
    "CAT",
    "MDT",
    "NEE",
    "SBUX",
    "LOW",
    "SPGI",
    "LIN",
    "GE",
    "COST",
    "UPS",
    "DE",
    "RTX",
    "MO",
    "CVS",
    "ZTS"
]


DEFAULT_PRICE_TRIGGER = 2.0
DEFAULT_SPREAD_TRIGGER = 0.5
DEFAULT_ATM_TRIGGER = 4.0


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


def _build_scan_result(symbol, current_price, previous_close, bid, ask, price_trigger, spread_trigger, atm_trigger):
    current_price = float(current_price)
    previous_close = float(previous_close)
    bid = float(bid)
    ask = float(ask)
    price_change = calculate_price_change(current_price, previous_close)
    spread = calculate_spread(bid, ask, current_price)
    liquidity = calculate_liquidity(bid, ask, current_price)
    atm_premium = (bid + ask) / 2
    price_triggered = bool(abs(price_change) >= price_trigger)
    liquidity_alert = bool(spread <= spread_trigger)
    atm_alert = bool(atm_premium >= atm_trigger)
    signal = "BUY ATM" if price_triggered and liquidity_alert and atm_alert else "NO ALERT"

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
        "reason": ", ".join(reasons) if reasons else "All filters passed"
    }


def _build_yfinance_result(symbol, price_trigger, spread_trigger, atm_trigger):
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="5d")
    if len(hist) < 2:
        return {
            "stock": symbol,
            "signal": "NO DATA",
            "reason": "Not enough price history"
        }

    previous_close = hist["Close"].iloc[-2]
    current_price = hist["Close"].iloc[-1]
    bid = current_price - random.uniform(0.2, 1.5)
    ask = current_price + random.uniform(0.2, 1.5)
    return _build_scan_result(
        symbol,
        current_price,
        previous_close,
        bid,
        ask,
        price_trigger,
        spread_trigger,
        atm_trigger
    )


def run_scanner(price_trigger=DEFAULT_PRICE_TRIGGER, spread_trigger=DEFAULT_SPREAD_TRIGGER, atm_trigger=DEFAULT_ATM_TRIGGER):
    results = []

    for symbol in STOCKS:
        if use_real:
            try:
                # Get stock historical data using Alpaca
                request = StockBarsRequest(
                    symbol_or_symbols=symbol,
                    timeframe=TimeFrame.Day,
                    limit=2
                )
                bars = stock_client.get_stock_bars(request_params=request).df
                if len(bars) < 2:
                    raise ValueError("Not enough Alpaca price history")
                previous_close = bars.iloc[-2]['close']
                current_price = bars.iloc[-1]['close']

                price_change = calculate_price_change(current_price, previous_close)

                if abs(price_change) >= price_trigger:
                    today = datetime.utcnow().date()
                    option_request = OptionChainRequest(
                        underlying_symbol=symbol,
                        expiration_date_gte=today
                    )
                    option_chain_response = option_client.get_option_chain(request_params=option_request)
                    option_contracts = []
                    if isinstance(option_chain_response, dict):
                        if 'contracts' in option_chain_response:
                            option_contracts = option_chain_response['contracts']
                        else:
                            option_contracts = list(option_chain_response.values())
                    elif isinstance(option_chain_response, list):
                        option_contracts = option_chain_response

                    call_contracts = []
                    for contract in option_contracts:
                        symbol_value = getattr(contract, 'symbol', None)
                        option_type = getattr(contract, 'type', None) or getattr(contract, 'option_type', None)
                        strike = getattr(contract, 'strike', None) or getattr(contract, 'strike_price', None)
                        exp_date = getattr(contract, 'expiration', None) or getattr(contract, 'expiration_date', None)

                        if option_type is not None and str(option_type).lower() != 'call' and str(option_type).lower() != 'contracttype.call':
                            continue
                        if strike is None or exp_date is None or symbol_value is None:
                            continue
                        call_contracts.append((contract, strike, symbol_value, exp_date))

                    if not call_contracts:
                        raise ValueError('No call contracts found')

                    closest_contract = min(call_contracts, key=lambda item: abs(item[1] - current_price))
                    option_symbol = closest_contract[2]

                    quote_request = OptionLatestQuoteRequest(symbol_or_symbols=option_symbol)
                    quote_response = option_client.get_option_latest_quote(request_params=quote_request)

                    if isinstance(quote_response, dict):
                        quote = quote_response.get(option_symbol) or list(quote_response.values())[0]
                    else:
                        quote = quote_response

                    if isinstance(quote, dict):
                        bid = quote.get('bid_price')
                        ask = quote.get('ask_price')
                    else:
                        bid = getattr(quote, 'bid_price', None)
                        ask = getattr(quote, 'ask_price', None)

                    if bid is None or ask is None or bid == 0 or ask == 0:
                        raise ValueError('Invalid option quote')

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
                else:
                    results.append(_build_scan_result(
                        symbol,
                        current_price,
                        previous_close,
                        current_price - random.uniform(0.2, 1.5),
                        current_price + random.uniform(0.2, 1.5),
                        price_trigger,
                        spread_trigger,
                        atm_trigger
                    ))
            except Exception as e:
                print(f"Real data error for {symbol}: {e}")
                # Fallback to yfinance
                try:
                    scan_result = _build_yfinance_result(symbol, price_trigger, spread_trigger, atm_trigger)
                    results.append(scan_result)
                    if scan_result.get("signal") == "BUY ATM":
                        _save_alert(scan_result)
                except Exception as e:
                    print(f"Fallback error for {symbol}: {e}")
                    results.append({
                        "stock": symbol,
                        "signal": "NO DATA",
                        "reason": str(e)
                    })
        else:
            # Original yfinance code
            try:
                scan_result = _build_yfinance_result(symbol, price_trigger, spread_trigger, atm_trigger)
                results.append(scan_result)
                if scan_result.get("signal") == "BUY ATM":
                    _save_alert(scan_result)
            except Exception as e:
                print(symbol, e)
                results.append({
                    "stock": symbol,
                    "signal": "NO DATA",
                    "reason": str(e)
                })

    return results
