# app.py
import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import requests

# Optional: For seasonality and PDF/CSV export
from io import BytesIO
import base64

# ---------------------- CONFIG ----------------------
WILLIAMS_PERIOD = 10
STOP_LOSS_PCT = 2
TARGET_PCT = 4
CRUDE_SYMBOL = "CL=F"  # WTI Crude
QUANDL_API_KEY = "your_quandl_api_key"  # Replace with your real key

# ---------------------- FUNCTIONS ----------------------
def fetch_crude_data():
    end = datetime.date.today()
    start = end - datetime.timedelta(weeks=52 * 2)
    df = yf.download(CRUDE_SYMBOL, start=start, end=end, interval="1wk")
    df = df.dropna()
    return df

def calculate_williams_r(df, period=WILLIAMS_PERIOD):
    high = df['High'].rolling(period).max()
    low = df['Low'].rolling(period).min()
    wr = -100 * (high - df['Close']) / (high - low)
    return wr

def get_cot_signal():
    url = f"https://www.quandl.com/api/v3/datasets/CFTC/067741_F_L_ALL.json?api_key={QUANDL_API_KEY}"
    r = requests.get(url)
    data = r.json()
    df = pd.DataFrame(data['dataset']['data'], columns=data['dataset']['column_names'])
    df['Date'] = pd.to_datetime(df['Date'])
    latest = df.iloc[0]
    commercials_net = latest['Producer/Merchant/Processor/User Longs'] - latest['Producer/Merchant/Processor/User Shorts']
    return "Long" if commercials_net > 0 else "Short", commercials_net

def get_seasonality(month):
    bullish_months = [3, 4, 7, 10, 11]  # Customize based on historical data
    return "Bullish" if month in bullish_months else "Neutral"

def detect_bullish_reversal(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    return last['Close'] > last['Open'] and last['Open'] < prev['Close'] and last['Close'] > prev['Open']

# ---------------------- STREAMLIT APP ----------------------
st.set_page_config(layout="centered")
st.title("🛢️ Larry Williams–Style Crude Oil Screener")

with st.spinner("Fetching data..."):
    df = fetch_crude_data()
    df['Williams %R'] = calculate_williams_r(df)
    wr_value = df['Williams %R'].iloc[-1]

    cot_signal, cot_net = get_cot_signal()
    seasonality = get_seasonality(df.index[-1].month)
    bullish_reversal = detect_bullish_reversal(df)

    buy_signal = (
        wr_value < -80 and
        cot_signal == "Long" and
        seasonality == "Bullish" and
        bullish_reversal
    )

    entry_price = df['Close'].iloc[-1]
    stop_loss = round(entry_price * (1 - STOP_LOSS_PCT / 100), 2)
    target = round(entry_price * (1 + TARGET_PCT / 100), 2)

st.subheader("📈 Latest Signal")
st.metric("Williams %R", f"{wr_value:.2f}")
st.metric("COT Signal", f"{cot_signal} ({cot_net})")
st.metric("Seasonality", seasonality)
st.metric("Bullish Reversal", "Yes" if bullish_reversal else "No")

st.markdown("---")
st.success("✅ **Buy Signal Detected!**" if buy_signal else "❌ No Signal This Week")
if buy_signal:
    st.markdown(f"**📍 Entry:** ₹{entry_price:.2f}  \n"
                f"🛑 **Stop Loss:** ₹{stop_loss:.2f}  \n"
                f"🎯 **Target:** ₹{target:.2f}")

# ---------------------- EXPORT OPTIONS ----------------------
results = pd.DataFrame([{
    "Date": df.index[-1].date(),
    "Close": entry_price,
    "Williams %R": wr_value,
    "COT Net": cot_net,
    "COT Signal": cot_signal,
    "Seasonality": seasonality,
    "Bullish Reversal": bullish_reversal,
    "Buy Signal": buy_signal,
    "Stop Loss": stop_loss,
    "Target": target
}])

csv = results.to_csv(index=False).encode()
st.download_button("📥 Download CSV", csv, "crude_signal.csv", "text/csv")

# PDF export placeholder (Streamlit doesn't support direct PDF export well)
# Later can use pdfkit or fpdf for real PDF generation
