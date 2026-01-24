import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import os
import requests
import xml.etree.ElementTree as ET
from tradingview_ta import TA_Handler, Interval, Exchange
import matplotlib

# [BACKEND SETUP]
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ==========================================
# 1. KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(
    page_title="TRADELOOP",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- PALET WARNA ---
PRIMARY_COLOR = "#3B82F6"
BG_DARK = "#0F172A"
PANEL_DARK = "#1E293B"
TEXT_COLOR = "#E2E8F0"
SUCCESS_COLOR = "#10B981"
DANGER_COLOR = "#EF4444"
WARN_COLOR = "#F59E0B"

st.markdown(f"""
<style>
    .stApp {{ background-color: {BG_DARK}; }}
    section[data-testid="stSidebar"] {{ background-color: {PANEL_DARK}; border-right: 1px solid rgba(255,255,255,0.05); }}
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] > div[data-testid="stVerticalBlock"] {{
        background-color: {PANEL_DARK}; border: 1px solid rgba(255,255,255,0.05); border-radius: 12px; padding: 24px;
    }}
    div[data-testid="stMetricValue"] {{ font-family: 'Inter', sans-serif; font-size: 1.8rem !important; font-weight: 700; color: {TEXT_COLOR} !important; }}
    div[data-testid="stMetricLabel"] {{ color: #94A3B8 !important; }}
    div.stButton > button {{ background-color: {PRIMARY_COLOR}; color: white; border: none; border-radius: 8px; height: 45px; font-weight: 600; }}
    .block-container {{ padding-top: 2rem; }}
    
    /* CARD STYLING */
    .plan-card {{
        background-color: #0f172a;
        border-left: 5px solid {PRIMARY_COLOR};
        padding: 15px; border-radius: 5px; margin-bottom: 10px;
    }}
    .fund-card {{
        background-color: #0f172a;
        border-right: 5px solid {WARN_COLOR};
        padding: 15px; border-radius: 5px; margin-bottom: 10px; text-align: right;
    }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATA ENGINE (FUNDAMENTAL + TECHNICAL)
# ==========================================
@st.cache_data(ttl=300)
def get_stock_data(ticker, period="1y"):
    try:
        y_ticker = f"{ticker}.JK" if not ticker.endswith(".JK") else ticker
        df = yf.download(y_ticker, period=period, interval="1d", progress=False, auto_adjust=True)
        if df is None or df.empty or len(df) < 15: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.rename(columns={'Open':'Open', 'High':'High', 'Low':'Low', 'Close':'Close', 'Volume':'Volume'}, inplace=True)
        df = df.dropna()
        if 'Close' not in df.columns: return None
        df['Close'] = df['Close'].astype(float)
        return df
    except: return None

@st.cache_data(ttl=86400)
def get_fundamentals(ticker):
    try:
        y_ticker = f"{ticker}.JK" if not ticker.endswith(".JK") else ticker
        stock = yf.Ticker(y_ticker)
        info = stock.info
        data = {
            "name": info.get('longName', ticker),
            "sector": info.get('sector', '-'),
            "pe": info.get('trailingPE', 0),
            "pbv": info.get('priceToBook', 0),
            "roe": info.get('returnOnEquity', 0),
            "div_yield": info.get('dividendYield', 0),
            "eps": info.get('trailingEps', 0),
            "book_value": info.get('bookValue', 0),
            "summary": info.get('longBusinessSummary', '-')
        }
        # Rumus Graham Number: Akar(22.5 x EPS x BVPS)
        if data['eps'] > 0 and data['book_value'] > 0:
            data['graham_num'] = np.sqrt(22.5 * data['eps'] * data['book_value'])
        else: data['graham_num'] = 0
        return data
    except: return None

def get_tv_analysis(ticker):
    try:
        handler = TA_Handler(symbol=ticker, screener="indonesia", exchange="IDX", interval=Interval.INTERVAL_1_DAY)
        analysis = handler.get_analysis()
        return analysis.summary.get('RECOMMENDATION', 'N/A'), analysis.summary
    except: return "N/A", {}

def get_news(ticker):
    try:
        # KITA TAMBAHKAN SUMBER TERPERCAYA BARU (Bisnis.com & Emitennews)
        sources = (
            "site:cnbcindonesia.com OR "
            "site:kontan.co.id OR "
            "site:investor.id OR "
            "site:bisnis.com OR "     # Bagus untuk info sektor/industri
            "site:emitennews.com OR " # Cepat untuk info RUPS/Dividen
            "site:idx.co.id"          # Sumber resmi
        )
        
        # Query Google News
        query = f"Saham {ticker} ({sources})"
        url = f"https://news.google.com/rss/search?q={query}&hl=id-ID&gl=ID&ceid=ID:id"
        
        resp = requests.get(url, timeout=4)
        root = ET.fromstring(resp.content)
        news = []
        
        for item in root.findall('./channel/item')[:7]: # Ambil 7 berita terbaru
            raw_title = item.find('title').text
            clean_title = raw_title.split(' - ')[0] if raw_title else "Berita Saham"
            
            # Membersihkan nama source agar rapi di UI
            src_raw = item.find('source').text if item.find('source') is not None else "News"
            src_clean = src_raw.replace("CNBC Indonesia", "CNBC").replace("Bisnis.com", "Bisnis").replace("KONTAN", "Kontan")
            
            news.append({
                'title': clean_title, 
                'link': item.find('link').text, 
                'pubDate': item.find('pubDate').text, 
                'source': src_clean
            })
        return news
    except: return []

def calculate_analytics(df):
    try:
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean().replace(0, 0.00001)
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        recent_vol = df['Volume'].tail(20)
        v_std = recent_vol.std() if recent_vol.std() != 0 else 1
        z_vol = (df['Volume'].iloc[-1] - recent_vol.mean()) / v_std
        
        y = df['Close'].tail(5).values
        slope, _ = np.polyfit(np.arange(len(y)), y, 1)
        
        # ATR Calculation (Volatilitas)
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        atr = true_range.rolling(14).mean().iloc[-1]
        
        return float(z_vol), float(slope), float(rsi.iloc[-1]), float(atr)
    except: return 0.0, 0.0, 50.0, 0.0

def calculate_hybrid_score(rsi, slope, z_vol, rec, fund_data, price):
    score = 0
    # 1. Technical (60 Poin Max)
    if rsi < 40: score += 15
    elif 40 <= rsi <= 60: score += 5
    if slope > 0: score += 15
    if z_vol > 1.5: score += 10
    if "BUY" in rec: score += 20
    elif "NEUTRAL" in rec: score += 5
    
    # 2. Fundamental (40 Poin Max)
    if fund_data:
        graham = fund_data.get('graham_num', 0)
        per = fund_data.get('pe', 0)
        pbv = fund_data.get('pbv', 0)
        
        if graham > price: score += 15 # Undervalued
        if 0 < per < 15: score += 15   # PER Wajar
        if 0 < pbv < 2.0: score += 10  # PBV Wajar
        
    return min(score, 100)

# ==========================================
# 3. SIDEBAR
# ==========================================
with st.sidebar:
    st.markdown("<h1 style='text-align: center; font-size: 50px;'>🛡️</h1>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; color: #E2E8F0; margin-top: -20px;'>SUPER TRADER</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748B; font-size: 0.8rem;'>v10.1 Hybrid Edition</p>", unsafe_allow_html=True)
    st.markdown("---")
    menu = st.radio("MENU", ["🚀 SCANNER", "📊 ANALISA LENGKAP", "⚙️ DATABASE"], index=0)

# ==========================================
# 4. HALAMAN UTAMA
# ==========================================

# --- SCANNER ---
if menu == "🚀 SCANNER":
    st.title("🚀 Pemindai (Tech + Fund)")
    st.caption("Skor memperhitungkan Teknikal (Tren) DAN Fundamental (Valuasi).")
    
    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        with c1:
            txt_files = [f for f in os.listdir('.') if f.endswith('.txt') and 'requirements' not in f]
            selected_file = st.selectbox("📂 WATCHLIST:", txt_files)
        with c2:
            st.write(""); st.write("")
            scan_btn = st.button("▶️ SCAN", use_container_width=True)

    if scan_btn:
        with open(selected_file, 'r') as f: tickers = [line.strip().upper() for line in f if line.strip()]
        results = []
        my_bar = st.progress(0, text="Processing...")
        
        for i, t in enumerate(tickers):
            my_bar.progress((i + 1) / len(tickers), text=f"Analyzing {t}...")
            try:
                df = get_stock_data(t, period="3mo")
                fund = get_fundamentals(t) # Ambil Fundamental juga saat scan
                if df is None: continue
                
                z_vol, slope, rsi, atr = calculate_analytics(df)
                rec, _ = get_tv_analysis(t)
                price = df['Close'].iloc[-1]
                
                # Hitung Skor Gabungan
                score = calculate_hybrid_score(rsi, slope, z_vol, rec, fund, price)
                
                status = "Wait"
                if score >= 75: status = "STRONG BUY"
                elif score >= 50: status = "BUY"
                
                # Info Fundamental Singkat untuk Tabel
                val_status = "Mahal"
                if fund and fund['graham_num'] > price: val_status = "Murah (Diskon)"
                
                results.append({
                    "Kode": t, "Harga": price, "Score": score, 
                    "Valuasi": val_status, "RSI": rsi, "Tren": slope
                })
            except: continue
        
        my_bar.empty()
        
        if results:
            df_res = pd.DataFrame(results).sort_values(by="Score", ascending=False)
            st.dataframe(df_res, use_container_width=True, column_config={
                "Harga": st.column_config.NumberColumn(format="Rp %d"),
                "Score": st.column_config.ProgressColumn("Hybrid Score", min_value=0, max_value=100, format="%d"),
                "RSI": st.column_config.NumberColumn(format="%.1f"),
                "Tren": st.column_config.NumberColumn(format="%.2f%%")
            })
        else: st.warning("Tidak ada data.")

# --- ANALISA LENGKAP (UI BARU: SPLIT VIEW) ---
elif menu == "📊 ANALISA LENGKAP":
    st.title("📊 Analisa 360° & Eksekusi")
    
    with st.container(border=True):
        c_in, c_go = st.columns([4, 1])
        with c_in: ticker = st.text_input("KODE SAHAM:", placeholder="Contoh: BBCA").upper().strip()
        with c_go: 
            st.write(""); st.write("")
            analyze = st.button("ANALISA 🔍", use_container_width=True)
            
    if analyze and ticker:
        with st.spinner("Menggabungkan data Teknikal & Fundamental..."):
            try:
                df = get_stock_data(ticker, period="1y")
                fund = get_fundamentals(ticker)
                
                if df is not None:
                    # Data Processing
                    z_vol, slope, rsi, atr = calculate_analytics(df)
                    rec, _ = get_tv_analysis(ticker)
                    price = df['Close'].iloc[-1]
                    chg_pct = ((price - df['Close'].iloc[-2])/df['Close'].iloc[-2])*100
                    total_score = calculate_hybrid_score(rsi, slope, z_vol, rec, fund, price)
                    
                    # Logic Trading Plan
                    stop_loss = int(round((price - (2 * atr)) / 5) * 5)
                    tp1 = int(round((price + (2 * atr)) / 5) * 5)
                    tp2 = int(round((price + (4 * atr)) / 5) * 5)
                    risk_pct = ((price - stop_loss) / price) * 100
                    
                    # Logic Fundamental
                    graham = fund['graham_num'] if fund else 0
                    diskon = ((graham - price) / graham) * 100 if graham > 0 else 0
                    
                    # --- UI LAYOUT ---
                    
                    # 1. HEADER (Score & Info)
                    c1, c2 = st.columns([1, 3])
                    with c1:
                        bg_c = SUCCESS_COLOR if total_score >= 70 else DANGER_COLOR if total_score <= 40 else WARN_COLOR
                        st.markdown(f"""
                        <div style="background:{bg_c}; padding:20px; border-radius:10px; text-align:center;">
                            <h1 style="color:white; margin:0;">{total_score}</h1>
                            <p style="color:white; margin:0;">Hybrid Score</p>
                        </div>
                        """, unsafe_allow_html=True)
                    with c2:
                        st.markdown(f"## {ticker} - Rp {price:,.0f} ({chg_pct:+.2f}%)")
                        if fund:
                            st.markdown(f"**{fund['name']}** | Sektor: {fund['sector']}")
                            st.caption(f"Rekomendasi Teknikal: {rec}")

                    st.markdown("---")

                    # 2. DUAL CARD (THE CORE FEATURE)
                    # Kiri: Trading Plan (Teknikal), Kanan: Fundamental Health (Valuasi)
                    col_tech, col_fund = st.columns(2)
                    
                    with col_tech:
                        st.subheader("🎯 Rencana Eksekusi (Teknikal)")
                        st.markdown(f"""
                        <div class="plan-card" style="border-left-color: {DANGER_COLOR};">
                            <strong>🛑 Stop Loss (SL)</strong><br>
                            <span style="font-size:1.5em">Rp {stop_loss:,.0f}</span> <small>(-{risk_pct:.1f}%)</small>
                        </div>
                        <div class="plan-card" style="border-left-color: {WARN_COLOR};">
                            <strong>📍 Entry Area</strong><br>
                            <span style="font-size:1.5em">Rp {price:,.0f}</span>
                        </div>
                        <div class="plan-card" style="border-left-color: {SUCCESS_COLOR};">
                            <strong>🚀 Take Profit (TP)</strong><br>
                            <span style="font-size:1.5em">Rp {tp1:,.0f} - {tp2:,.0f}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        if risk_pct > 10: st.warning("⚠️ Volatilitas tinggi! Kecilkan porsi lot.")

                    with col_fund:
                        st.subheader("🏢 Kesehatan Valuasi (Fundamental)")
                        if fund:
                            # Warna indikator fundamental
                            g_color = SUCCESS_COLOR if diskon > 0 else DANGER_COLOR
                            per_color = SUCCESS_COLOR if 0 < fund['pe'] < 15 else WARN_COLOR
                            
                            st.markdown(f"""
                            <div class="fund-card" style="border-right-color: {g_color};">
                                <strong>⚖️ Harga Wajar (Graham)</strong><br>
                                <span style="font-size:1.5em">Rp {graham:,.0f}</span><br>
                                <small style="color:{g_color}">Status: {"Diskon " + str(round(diskon,1)) + "%" if diskon > 0 else "Mahal (Premium)"}</small>
                            </div>
                            <div class="fund-card" style="border-right-color: {per_color};">
                                <strong>📊 PER & PBV</strong><br>
                                <span style="font-size:1.2em">PER: {fund['pe']:.1f}x | PBV: {fund['pbv']:.1f}x</span>
                            </div>
                            <div class="fund-card" style="border-right-color: #3B82F6;">
                                <strong>💰 Profitabilitas & Dividen</strong><br>
                                <span style="font-size:1.2em">ROE: {fund['roe']*100:.1f}% | Div: {fund['div_yield']*100:.1f}%</span>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.info("Data fundamental tidak tersedia.")

                    # 3. CHART & NEWS
                    st.write("")
                    tab1, tab2 = st.tabs(["📈 CHART", "📰 BERITA"])
                    
                    with tab1:
                        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name=ticker)])
                        fig.add_hline(y=stop_loss, line_dash="dash", line_color="red", annotation_text="Stop Loss")
                        fig.add_hline(y=tp1, line_dash="dash", line_color="green", annotation_text="TP 1")
                        fig.update_layout(title=f"Chart & Plan {ticker}", template="plotly_dark", height=500, xaxis_rangeslider_visible=False)
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with tab2:
                        news = get_news(ticker)
                        if news:
                             for n in news:
                                with st.container(border=True):
                                    st.markdown(f"**{n['title']}**")
                                    c_d, c_s, c_l = st.columns([2, 2, 1])
                                    with c_d: st.caption(n['pubDate'])
                                    with c_s: st.caption(n['source'])
                                    with c_l: st.link_button("Baca", n['link'])
                        else: st.info("Tidak ada berita.")

                else: st.error("Saham tidak ditemukan.")
            except Exception as e: st.error(f"Error: {e}")

# --- DATABASE ---
elif menu == "⚙️ DATABASE":
    st.title("⚙️ Pengaturan")
    with st.container(border=True):
        txt_files = [f for f in os.listdir('.') if f.endswith('.txt') and 'requirements' not in f]
        file_to_edit = st.selectbox("Edit File:", txt_files)
        if file_to_edit:
            with open(file_to_edit, "r") as f: current = f.read()
            new = st.text_area("Isi:", value=current, height=300)
            if st.button("💾 Simpan"):
                with open(file_to_edit, "w") as f: f.write(new)
                st.toast("Tersimpan!", icon="✅")