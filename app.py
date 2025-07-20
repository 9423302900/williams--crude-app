import streamlit as st import pandas as pd import yfinance as yf import requests import datetime import plotly.graph_objects as go

=== CONFIG ===

SYMBOL = "CL=F"  # Crude Oil Futures WILLIAMS_PERIOD = 10 STOP_LOSS_PCT = 2 TARGET_PCT = 4 QUANDL_API_KEY = "your_api_key_here"  # 🔑 Replace with your Quandl API key

=== FUNCTION: COT Signal ===

def get_cot_signal(): try: url = f"https://www.quandl.com/api/v3/datasets/CFTC/067651_F_L_ALL.json?api_key={QUANDL_API_KEY}" r = requests.get(url) r.raise_for_status() json_data = r.json()

df = json_data['dataset']['data']
    headers = json_data['dataset']['column_names']
    last = df[0]
    net_position = last[headers.index("Noncommercial Positions-Long")] - last[headers.index("Noncommercial Positions-Short")]

    signal = "BUY" if net_position > 0 else "SELL"
    return signal, net_position

except Exception as e:
    print("❌ Error getting COT data:", e)
    return "UNKNOWN", 0

=== FUNCTION: Seasonality (Mocked) ===

def get_seasonality_signal(): month = datetime.datetime.today().month bullish_months = [2, 3, 4, 8, 9, 10]  # Hypothetical return "BUY" if month in bullish_months else "SELL"

=== FUNCTION: Williams %R ===

def calculate_williams_r(df, period=WILLIAMS_PERIOD): high = df['High'].rolling(window=period).max() low = df['Low'].rolling(window=period).min() r = -100 * ((high - df['Close']) / (high - low)) return r

=== FUNCTION: Generate Signals ===

def generate_signals(df): df['Williams %R'] = calculate_williams_r(df) df['Signal'] = 'HOLD' df.loc[df['Williams %R'] < -80, 'Signal'] = 'BUY' df.loc[df['Williams %R'] > -20, 'Signal'] = 'SELL' return df

=== STREAMLIT UI ===

st.set_page_config(page_title="Larry Williams Crude Oil Screener", layout="wide") st.title("🛢️ Larry Williams–Style Crude Oil Screener")

with st.spinner("Loading data..."): data = yf.download(SYMBOL, period="6mo", interval="1d") data.dropna(inplace=True) df = generate_signals(data.copy()) cot_signal, cot_net = get_cot_signal() season_signal = get_seasonality_signal()

=== DISPLAY SIGNALS ===

st.subheader("🔍 Combined Signal") st.metric("📈 COT Signal", cot_signal) st.metric("📅 Seasonal Signal", season_signal)

latest_signal = df.iloc[-1]['Signal'] st.metric("📊 Williams %R Signal", latest_signal)

=== STRATEGY BACKTEST ===

def backtest(df): trades = [] entry = None for i in range(1, len(df)): if df['Signal'].iloc[i-1] != 'BUY' and df['Signal'].iloc[i] == 'BUY': entry = df['Close'].iloc[i] entry_date = df.index[i] sl = entry * (1 - STOP_LOSS_PCT / 100) tgt = entry * (1 + TARGET_PCT / 100) elif entry: price = df['Close'].iloc[i] if price <= sl: trades.append((entry_date, 'SL', entry, price)) entry = None elif price >= tgt: trades.append((entry_date, 'TARGET', entry, price)) entry = None return pd.DataFrame(trades, columns=["Entry Date", "Exit Type", "Entry Price", "Exit Price"])

backtest_df = backtest(df) st.subheader("📉 Backtest Results") st.dataframe(backtest_df)

=== PLOT ===

fig = go.Figure() fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name='Close Price')) fig.add_trace(go.Scatter(x=df.index, y=df['Williams %R'], name='Williams %R', yaxis="y2")) fig.update_layout(title="Crude Oil + Williams %R", yaxis2=dict(overlaying='y', side='right')) st.plotly_chart(fig, use_container_width=True)

=== EXPORT ===

st.subheader("📤 Export") st.download_button("Download Signals CSV", df.to_csv().encode(), "signals.csv") st.download_button("Download Backtest CSV", backtest_df.to_csv().encode(), "backtest.csv")

