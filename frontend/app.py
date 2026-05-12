import os

import pandas as pd
import requests
import streamlit as st

backend_hostport = os.getenv("BACKEND_HOSTPORT")
BACKEND_URL = os.getenv(
    "BACKEND_URL",
    f"http://{backend_hostport}" if backend_hostport else "http://backend:8000",
).rstrip("/")


def backend_urls():
    urls = [BACKEND_URL]

    if backend_hostport:
        backend_host = backend_hostport.split(":", 1)[0]
        public_render_url = f"https://{backend_host}.onrender.com"
        if public_render_url not in urls:
            urls.append(public_render_url)

    return urls

st.set_page_config(page_title="Options Flow Screener", layout="wide")

st.markdown(
    """
    <style>
    .dashboard-card { background: #ffffff; border-radius: 8px; padding: 20px; box-shadow: 0 14px 34px rgba(20, 32, 70, 0.08); margin-bottom: 18px; }
    .metric-card { background: #f8fafc; border-radius: 8px; padding: 18px; text-align: center; border: 1px solid #e5e7eb; }
    .metric-card strong { display: block; font-size: 28px; margin-bottom: 6px; }
    .metric-card span { color: #6b7280; }
    .status-pill { display: inline-block; border-radius: 999px; padding: 6px 12px; font-size: 12px; font-weight: 700; white-space: nowrap; }
    .pill-green { background: #ecfdf5; color: #166534; }
    .pill-red { background: #fef2f2; color: #b91c1c; }
    .pill-yellow { background: #fef9c3; color: #7c2d12; }
    .alert-box { background: #fff7ed; border-radius: 8px; padding: 14px; margin-top: 14px; color: #7c2d12; }
    .stat-label { color: #6b7280; font-size: 14px; }
    .card-row { display: flex; flex-wrap: wrap; gap: 18px; }
    .card-row .dashboard-card { flex: 1 1 45%; min-width: 300px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Options Flow Screener")
st.write("Morning scan checks price change, liquidity, and ATM premium for every configured stock.")

col1, col2, col3 = st.columns([1, 1, 1])
price_trigger = col1.slider("Price trigger (%)", 0.5, 10.0, 2.0, 0.1)
spread_trigger = col2.slider("Bid/Ask spread (%)", 0.1, 5.0, 0.5, 0.1)
atm_trigger = col3.slider("ATM premium", 0.5, 500.0, 4.0, 0.5)


def fetch_scan():
    last_error = None
    for url in backend_urls():
        try:
            response = requests.get(
                f"{url}/scan",
                params={
                    "price_trigger": price_trigger,
                    "spread_trigger": spread_trigger,
                    "atm_trigger": atm_trigger,
                },
                timeout=180,
            )
            response.raise_for_status()
            return response.json()
        except Exception as ex:
            last_error = ex

    raise last_error


def fetch_alerts():
    last_error = None
    for url in backend_urls():
        try:
            response = requests.get(f"{url}/alerts", timeout=20)
            response.raise_for_status()
            return response.json()
        except Exception as ex:
            last_error = ex

    raise last_error


scan_button = st.button("Rescan")

if scan_button:
    with st.spinner("Scanning market..."):
        try:
            scan_data = fetch_scan()
        except Exception as ex:
            st.error(f"Unable to reach backend: {ex}")
            scan_data = []

    if scan_data:
        st.success(f"{len(scan_data)} stocks scanned")
    else:
        st.info("No scan data returned.")

    st.session_state["scan_data"] = scan_data

if "scan_data" not in st.session_state:
    try:
        st.session_state["scan_data"] = fetch_scan()
    except Exception:
        st.session_state["scan_data"] = []

scan_data = st.session_state.get("scan_data", [])

total_stocks = len(scan_data)
price_triggered = len([item for item in scan_data if item.get("price_triggered")])
liquidity_alert = len([item for item in scan_data if item.get("liquidity_alert")])
atm_alert = len([item for item in scan_data if item.get("atm_alert")])

stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
with stats_col1:
    st.markdown(
        f"<div class='metric-card'><strong>{total_stocks}</strong><span>Total scanned</span></div>",
        unsafe_allow_html=True,
    )
with stats_col2:
    st.markdown(
        f"<div class='metric-card'><strong>{price_triggered}</strong><span>Price triggered</span></div>",
        unsafe_allow_html=True,
    )
with stats_col3:
    st.markdown(
        f"<div class='metric-card'><strong>{liquidity_alert}</strong><span>Liquidity passed</span></div>",
        unsafe_allow_html=True,
    )
with stats_col4:
    st.markdown(
        f"<div class='metric-card'><strong>{atm_alert}</strong><span>ATM premium passed</span></div>",
        unsafe_allow_html=True,
    )

filter_options = ["All scanned", "Buy ATM", "Price triggered", "Liquidity alert", "ATM premium alert", "No data"]
active_filter = st.radio("Show", filter_options, horizontal=True)

if active_filter == "Buy ATM":
    filtered_data = [item for item in scan_data if item.get("signal") == "BUY ATM"]
elif active_filter == "Price triggered":
    filtered_data = [item for item in scan_data if item.get("price_triggered")]
elif active_filter == "Liquidity alert":
    filtered_data = [item for item in scan_data if item.get("liquidity_alert")]
elif active_filter == "ATM premium alert":
    filtered_data = [item for item in scan_data if item.get("atm_alert")]
elif active_filter == "No data":
    filtered_data = [item for item in scan_data if item.get("signal") == "NO DATA"]
else:
    filtered_data = scan_data

st.markdown("<div class='card-row'>", unsafe_allow_html=True)

if not filtered_data:
    st.warning("No stocks to show for the selected filter and thresholds.")
else:
    for alert in filtered_data:
        change = alert.get("change_percent", 0)
        change_color = "#15803d" if change >= 0 else "#b91c1c"
        status_label = alert.get("signal", "NO ALERT")

        if status_label == "BUY ATM":
            status_html = "<span class='status-pill pill-green'>BUY ATM</span>"
        elif status_label == "NO DATA":
            status_html = "<span class='status-pill pill-red'>NO DATA</span>"
        else:
            status_html = "<span class='status-pill pill-yellow'>NO ALERT</span>"

        if status_label == "BUY ATM":
            alert_box_html = (
                "<div class='alert-box'><strong>ATM premium alert</strong><br />"
                "Premium: {atm:.2f} | Spread: {spread:.2f}%</div>".format(
                    atm=alert.get("atm_premium", 0),
                    spread=alert.get("spread", 0),
                )
            )
        elif alert.get("reason"):
            alert_box_html = "<div class='alert-box'>{}</div>".format(alert.get("reason"))
        else:
            alert_box_html = ""

        html = """
            <div class='dashboard-card'>
                <div style='display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:16px;'>
                    <div>
                        <div style='font-size:18px; font-weight:700;'>{stock}</div>
                        <div style='color:#6b7280;'>Price trigger | Liquidity | ATM premium</div>
                    </div>
                    {status_html}
                </div>
                <div style='display:flex; justify-content:space-between; gap:16px; flex-wrap:wrap; margin-bottom:16px;'>
                    <div><strong style='font-size:24px;'>${price:.2f}</strong><div class='stat-label'>Current price</div></div>
                    <div><strong style='font-size:24px; color:{change_color};'>{change:+.2f}%</strong><div class='stat-label'>Day change</div></div>
                    <div><strong style='font-size:24px;'>{atm_strike}</strong><div class='stat-label'>ATM strike</div></div>
                </div>
                <div style='display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:12px;'>
                    <div style='padding:14px; background:#f8fafc; border-radius:8px;'>
                        <div style='font-size:12px; color:#6b7280;'>BID / ASK</div>
                        <div style='font-weight:700; margin-top:6px;'>{bid:.2f} / {ask:.2f}</div>
                    </div>
                    <div style='padding:14px; background:#f8fafc; border-radius:8px;'>
                        <div style='font-size:12px; color:#6b7280;'>SPREAD</div>
                        <div style='font-weight:700; margin-top:6px;'>{spread:.2f}%</div>
                    </div>
                    <div style='padding:14px; background:#f8fafc; border-radius:8px;'>
                        <div style='font-size:12px; color:#6b7280;'>LIQUIDITY</div>
                        <div style='font-weight:700; margin-top:6px;'>{liquidity:.2f}%</div>
                    </div>
                    <div style='padding:14px; background:#f8fafc; border-radius:8px;'>
                        <div style='font-size:12px; color:#6b7280;'>ATM PREMIUM</div>
                        <div style='font-weight:700; margin-top:6px;'>{atm_prem:.2f}</div>
                    </div>
                </div>
                {alert_box_html}
            </div>
        """.format(
            stock=alert.get("stock", ""),
            price=alert.get("price", 0),
            change_color=change_color,
            change=change,
            atm_strike=alert.get("atm", ""),
            bid=alert.get("bid", 0),
            ask=alert.get("ask", 0),
            spread=alert.get("spread", 0),
            liquidity=alert.get("liquidity", 0),
            atm_prem=alert.get("atm_premium", 0),
            status_html=status_html,
            alert_box_html=alert_box_html,
        )

        st.markdown(html, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")

st.header("Database Alerts")
try:
    all_data = fetch_alerts()
    if all_data:
        df_all = pd.DataFrame(all_data)
        st.dataframe(df_all)
    else:
        st.info("No alerts in database yet.")
except Exception as ex:
    st.error(f"Unable to load saved alerts: {ex}")
