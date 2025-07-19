


import streamlit as st import pandas as pd import yfinance as yf from fpdf import FPDF import io import gspread from oauth2client.service_account import ServiceAccountCredentials

--- SETTINGS ---

STOP_LOSS_PCT = 2 TARGET_PCT = 4 WILLIAMS_PERIOD = 10

--- Fetch Crude Oil Data ---

def get_crude_data(): crude = yf.download("CL=F", period="6mo", interval="1d") crude.dropna(inplace=True) return crude

--- Williams %R ---

def williams_r(df, period=WILLIAMS_PERIOD): high = df['High'].rolling(period).max() low = df['Low'].rolling(period).min() wr = -100 * (high - df['Close']) / (high - low) df['williams_r'] = wr return df

--- Generate Buy Signals ---

def generate_signals(df): df['Signal'] = None for i in range(1, len(df)): if df['williams_r'].iloc[i-1] > -20 and df['williams_r'].iloc[i] < -80: df.at[df.index[i], 'Signal'] = 'Buy' return df

--- Backtest ---

def backtest_strategy(data, stop_loss_pct=STOP_LOSS_PCT, target_pct=TARGET_PCT): trades = [] for i in range(len(data)): if data['Signal'].iloc[i] == 'Buy': entry_date = data.index[i] entry_price = data['Close'].iloc[i] stop_loss = entry_price * (1 - stop_loss_pct / 100) target = entry_price * (1 + target_pct / 100)

exit_price, exit_date, reason = None, None, None
        for j in range(1, 6):
            if i + j >= len(data):
                break
            curr_price = data['Close'].iloc[i + j]
            if curr_price <= stop_loss:
                exit_price = curr_price
                exit_date = data.index[i + j]
                reason = 'Stop Loss'
                break
            elif curr_price >= target:
                exit_price = curr_price
                exit_date = data.index[i + j]
                reason = 'Target Hit'
                break
            elif data['williams_r'].iloc[i + j] > -20 or j == 5:
                exit_price = curr_price
                exit_date = data.index[i + j]
                reason = 'Time/Overbought'
                break

        if exit_price:
            pnl = exit_price - entry_price
            return_pct = (pnl / entry_price) * 100
            trades.append({
                'Entry Date': entry_date,
                'Exit Date': exit_date,
                'Entry Price': round(entry_price, 2),
                'Exit Price': round(exit_price, 2),
                'PnL': round(pnl, 2),
                'Return %': round(return_pct, 2),
                'Exit Reason': reason
            })

return pd.DataFrame(trades)

--- PDF Report ---

def create_pdf(df, title="Signals Report"): pdf = FPDF() pdf.add_page() pdf.set_font("Arial", size=12) pdf.set_title(title) pdf.cell(200, 10, txt=title, ln=True, align='C') for col in df.columns: pdf.cell(40, 10, col, 1, 0, 'C') pdf.ln() for i in range(len(df)): for col in df.columns: cell = str(df.iloc[i][col]) pdf.cell(40, 10, cell[:15], 1, 0, 'C') pdf.ln() buffer = io.BytesIO() pdf.output(buffer) buffer.seek(0) return buffer

--- Streamlit App ---

st.set_page_config(layout="wide") st.title("🛢️ Larry Williams Crude Oil Strategy")

crude = get_crude_data() williams_r(crude) signals = generate_signals(crude) st.subheader("📉 Signal Table") st.dataframe(signals[signals['Signal'] == 'Buy'])

Export signals CSV/PDF

if not signals.empty: csv_signals = signals.to_csv(index=False).encode('utf-8') st.download_button("⬇️ Download Signals CSV", csv_signals, "signals.csv") pdf_signals = create_pdf(signals[signals['Signal'] == 'Buy']) st.download_button("📄 Download Signals PDF", pdf_signals, "signals.pdf")

Backtest

st.subheader("📊 Backtest") sl = st.slider("Stop Loss %", 1, 10, STOP_LOSS_PCT) tp = st.slider("Target %", 2, 15, TARGET_PCT) bt_result = backtest_strategy(signals, sl, tp) st.dataframe(bt_result)

Export backtest CSV/PDF

if not bt_result.empty: csv_bt = bt_result.to_csv(index=False).encode('utf-8') st.download_button("⬇️ Download Backtest CSV", csv_bt, "backtest.csv") pdf_bt = create_pdf(bt_result, title="Backtest Report") st.download_button("📄 Download Backtest PDF", pdf_bt, "backtest.pdf")

--- Google Sheet Export ---

if st.button("📤 Export Backtest to Google Sheets"): try: scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"] creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope) client = gspread.authorize(creds) sheet = client.open("Williams Crude Signals") try: bt_ws = sheet.worksheet("Backtest") except: bt_ws = sheet.add_worksheet(title="Backtest", rows="100", cols="20") bt_ws.clear() bt_ws.update([bt_result.columns.values.tolist()] + bt_result.values.tolist()) st.success("✅ Backtest exported to Google Sheets") except Exception as e: st.error(f"❌ Export failed: {e}")

