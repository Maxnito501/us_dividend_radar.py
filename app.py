# -*- coding: utf-8 -*-
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# --- 1. ตั้งค่าหน้าเว็บ (ปรับให้เหมาะกับทั้งหน้าจอคอมพิวเตอร์และมือถือแบบ Hybrid) ---
st.set_page_config(page_title="US Dividend Radar V1.0", page_icon="🇺🇸", layout="wide")

# Custom CSS (คงความ Clean พรีเมียม พิทักษ์ภัยพอร์ตสายตา)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;600&display=swap');
    html, body, [class*="css"]  { font-family: 'Kanit', sans-serif; }
    .status-box { padding: 15px; border-radius: 15px; text-align: center; font-weight: bold; margin-bottom: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .buy-box { background-color: #dcfce7; color: #166534; border: 1px solid #166534; }
    .sell-box { background-color: #fee2e2; color: #991b1b; border: 1px solid #991b1b; }
    .wait-box { background-color: #f3f4f6; color: #374151; border: 1px solid #6b7280; }
    .hold-box { background-color: #e0f2fe; color: #1e40af; border: 1px solid #1e40af; }
</style>
""", unsafe_allow_html=True)

st.title("🇺🇸 US Dividend Radar V1.0")
st.markdown("**ระบบสแกนดักจังหวะย่อซื้อ (Buy on Dip) กองทุนปันผลคู่ใจของแฟนพี่โบ้**")
st.write("---")

# --- 2. ฐานข้อมูลขุนพลคู่หู (บีบเหลือแค่ 2 กองทุนหลักอเมริกาตามใบสั่งเด็ดขาด) ---
STOCK_DB = {
    "SCHD": {"Type": "Dividend-Growth", "Name": "SCHD (Dividend Growth King)"},
    "JEPQ": {"Type": "Monthly-Premium", "Name": "JEPQ (Nasdaq Covered Call Income)"}
}

ALL_TICKERS = list(STOCK_DB.keys())

# --- 3. เครื่องยนต์ดึงข้อมูลและวิเคราะห์คณิตศาสตร์สถิติดิบ ---
@st.cache_data(ttl=1800) # ปรับแคชความสดดาต้าเหลือ 30 นาทีเพื่อความกริบ
def fetch_batch_data(tickers):
    try:
        data = yf.download(tickers, period="1y", interval="1d", group_by='ticker', auto_adjust=True, progress=False)
        return data
    except: return None

def process_indicator(batch_data, ticker):
    try:
        if len(ALL_TICKERS) == 1: df = batch_data
        else: df = batch_data[ticker].copy()
        if df.empty or len(df) < 50: return None
        df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
        df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['Vol_SMA20'] = df['Volume'].rolling(20).mean()
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        return df
    except: return None

# --- 4. หน้าหลัก: แผงควบคุมตรวจจับพิกัดความเร็วโมเมนตัม ---
st.subheader("📊 Tactical Monitor: คู่หูปั๊มเงินสดปันผลโลก")

with st.spinner('กำลังสแกนดุลราคาฝั่งสหรัฐฯ...'):
    batch_data = fetch_batch_data(ALL_TICKERS)

if batch_data is not None:
    data_rows = []
    for ticker in ALL_TICKERS:
        df = process_indicator(batch_data, ticker)
        if df is not None:
            price = df['Close'].iloc[-1]
            rsi = df['RSI'].iloc[-1]
            ema200 = df['EMA200'].iloc[-1]
            vol_today = df['Volume'].iloc[-1]
            vol_sma = df['Vol_SMA20'].iloc[-1]
            info = STOCK_DB[ticker]
            vol_status = "🐳 วาฬเข้าสอย!" if vol_today > (vol_sma * 1.5) else "ปกติ"
            trend = "🐂 ขาขึ้นแกร่ง" if price > ema200 else "🐻 ขาลงพักฐาน"
            action = "Wait"
            status_color = "white"
            
            # ล็อกเงื่อนไขวินัยสากล ช้อนก้นเหวยาม RSI ย่อตัว
            if rsi <= 40: # ขยายเกณฑ์แนวรับ RMF/ETF ต่างประเทศให้เก็บของง่ายขึ้น
                action = "🟢 BUY DIP (จังหวะสับไกช้อนของถูก!)"
                status_color = "#dcfce7"
            elif rsi >= 70:
                action = "🔴 TAKE PROFIT (โซนตึงตัวเฉือนขาย)"
                status_color = "#fee2e2"
            elif 40 < rsi <= 50 and price > ema200:
                action = "🛒 ACCUMULATE (สะสมพลังงาน DCA เพิ่ม)"
                status_color = "#e0f2fe"
            else:
                action = "⏳ HOLD & DCA ON TIMING (ถือรันวินัยปกติ)"
                status_color = "#f3f4f6"
                
            data_rows.append({
                "Category": info['Type'], "Symbol": info['Name'], "Ticker": ticker, 
                "Price": price, "RSI": rsi, "Volume": vol_status, "Trend": trend, 
                "Action": action, "Color": status_color
            })

    if data_rows:
        res_df = pd.DataFrame(data_rows)
        st.dataframe(
            res_df.style.apply(lambda r: [f'background-color: {r["Color"]}']*len(r), axis=1).format({"Price": "${:,.2f}", "RSI": "{:.1f}"}),
            column_order=["Category", "Symbol", "Price", "RSI", "Volume", "Trend", "Action"],
            height=200, use_container_width=True
        )

        # --- 5. เจาะลึกเลดาร์เทคนิคัลรายตัว & วินิจฉัยพอร์ตสำหรับแฟนพี่โบ้ ---
        st.write("---")
        col_chart, col_doc = st.columns([2, 1])
        
        with col_chart:
            st.subheader("🔍 Technical Radar")
            selected_name = st.selectbox("เลือกม้าศึกส่องกล้อง:", res_df['Symbol'])
            selected_ticker = res_df[res_df['Symbol'] == selected_name]['Ticker'].values[0]
            df_chart = process_indicator(batch_data, selected_ticker)
            
            if df_chart is not None:
                fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.6, 0.2, 0.2])
                fig.add_trace(go.Candlestick(x=df_chart.index, open=df_chart['Open'], high=df_chart['High'], low=df_chart['Low'], close=df_chart['Close'], name='Price'), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['EMA20'], name='EMA 20 (เส้นซิ่ง)', line=dict(color='orange', width=1)), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['EMA200'], name='EMA 200 (รากแก้ว)', line=dict(color='blue', width=2)), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['RSI'], name='RSI', line=dict(color='purple')), row=2, col=1)
                fig.add_hline(y=30, line_dash="dot", line_color="green", row=2, col=1)
                fig.add_hline(y=70, line_dash="dot", line_color="red", row=2, col=1)
                v_colors = ['green' if df_chart['Close'].iloc[i] > df_chart['Open'].iloc[i] else 'red' for i in range(len(df_chart))]
                fig.add_trace(go.Bar(x=df_chart.index, y=df_chart['Volume'], name='Volume', marker_color=v_colors), row=3, col=1)
                fig.update_layout(height=550, xaxis_rangeslider_visible=False, template="plotly_white", margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig, use_container_width=True)

        with col_doc:
            st.subheader("👨‍⚕️ Tactical Doctor")
            st.info(f"กองทุน: **{selected_name}**")
            avg_cost = st.number_input("ใส่ต้นทุนเฉลี่ยของพอร์ต ($)", value=0.0, format="%.2f", key="cost_input")
            qty = st.number_input("จำนวนหน่วยที่ถืออยู่", value=0.0, step=1.0, key="qty_input")
            curr_price = df_chart['Close'].iloc[-1]
            
            if qty > 0 and avg_cost > 0:
                unrealized = (curr_price - avg_cost) * qty
                pct = (unrealized / (avg_cost * qty)) * 100
                if unrealized < 0:
                    st.error(f"📉 สถานะ: ขาดทุนทางบัญชี {pct:.2f}% (${abs(unrealized):,.2f})")
                    if df_chart['RSI'].iloc[-1] <= 40:
                        st.markdown('<div class="status-box buy-box">💉 คำสั่งรบ: RSI ต่ำติดดินตามเป้า! สับไก DCA อัดกระสุนเพิ่มจังหวะย่อทองคำ!</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="status-box wait-box">⏳ คำสั่งรบ: นั่งทับมือนิ่ง ๆ ปล่อยให้ระบบ DCA ทำงานตามรอบปกติ ไม่รีบเติมเงิน</div>', unsafe_allow_html=True)
                else:
                    st.success(f"🎉 สถานะ: กำไรสะสมหล่อ ๆ {pct:.2f}% (${unrealized:,.2f})")
                    st.markdown('<div class="status-box hold-box">🛡️ คำสั่งรบ: ห้ามขายหมู! นอนกอดกินเงินปันผลทบต้นเพื่อปี 2035 ยาวไปครับ</div>', unsafe_allow_html=True)
            else:
                st.caption("ป้อนข้อมูลหน้าตักของแฟนพี่โบ้เพื่อรับใบสั่งรบตามระบบหลังบ้าน Jarvis")

else:
    st.error("ดาวเทียมตรวจจับตลาดหุ้นอเมริกาขัดข้อง กรุณาตรวจสอบการเชื่อมต่ออินเทอร์เน็ต")

st.markdown("---")
st.caption("Created by Suchat50 for Commander Bo & Family | 'วินัยเหล็กคุมเลเยอร์เวลา คือคีย์หลักของการเป็นผู้ชนะเหนือตลาด'")
