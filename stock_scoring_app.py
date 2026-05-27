import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# =========================
# ページ設定
# =========================
st.set_page_config(
    page_title="Stock Scoring App",
    layout="wide"
)

# =========================
# データ取得
# =========================
def get_data(ticker, period="2y"):

    df = yf.download(
        ticker,
        period=period,
        auto_adjust=True
    )

    # MultiIndex対策
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # 必要列だけ残す
    df = df[["Open", "High", "Low", "Close", "Volume"]]

    df = df.dropna()

    return df


# =========================
# 指標計算
# =========================
def add_indicators(df):

    df = df.copy()

    # 移動平均
    df["MA50"] = df["Close"].rolling(50).mean()
    df["MA200"] = df["Close"].rolling(200).mean()

    # 52週高値
    df["52w_high"] = df["Close"].rolling(252).max()
    df["high_ratio"] = df["Close"] / df["52w_high"]

    # RSI
    delta = df["Close"].diff()

    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss

    df["RSI"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()

    df["MACD"] = ema12 - ema26
    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_signal"]

    # 出来高平均
    df["vol_ma20"] = df["Volume"].rolling(20).mean()

    return df


# =========================
# スコアリング
# =========================
def score_latest(df):

    row = df.iloc[-1]

    score = 0
    detail = {}

    # =====================
    # トレンド
    # =====================

    if row["Close"] > row["MA200"]:
        score += 3
        detail["株価 > MA200"] = 3

    if row["MA50"] > row["MA200"]:
        score += 2
        detail["MA50 > MA200"] = 2

    if row["Close"] > row["MA50"]:
        score += 2
        detail["株価 > MA50"] = 2

    if row["high_ratio"] >= 0.8:
        score += 1
        detail["52週高値圏"] = 1

    # =====================
    # モメンタム
    # =====================

    rsi = row["RSI"]

    if 50 <= rsi <= 70:
        score += 3
        detail["RSI良好"] = 3

    elif 40 <= rsi < 50:
        score += 1
        detail["RSI中立"] = 1

    elif rsi <= 30:
        score += 2
        detail["RSI売られすぎ"] = 2

    if row["MACD_hist"] > 0:
        score += 2
        detail["MACDプラス"] = 2

    # =====================
    # 出来高
    # =====================

    if row["Volume"] > row["vol_ma20"] * 1.5:
        score += 2
        detail["出来高急増"] = 2

    # =====================
    # 判定
    # =====================

    if score >= 16:
        label = "🟢 強い買い"

    elif score >= 12:
        label = "🟢 買い"

    elif score >= 10:
        label = "🟡 買い増し検討"

    elif score >= 7:
        label = "⏸ 静観"

    elif score >= 4:
        label = "🔴 売り検討"

    else:
        label = "❌ 売り"

    return score, label, detail


# =========================
# UI
# =========================

st.title("📊 定量スコア型 株分析アプリ")

st.write("長期投資向けテクニカル分析スコアリング")

ticker = st.text_input(
    "ティッカー（例：AAPL, MSFT, NVDA）",
    "AAPL"
)

period = st.selectbox(
    "期間",
    ["1y", "2y", "5y"],
    index=1
)

# =========================
# 分析実行
# =========================

if st.button("分析開始"):

    try:

        # データ取得
        with st.spinner("データ取得中..."):

            df = get_data(ticker, period)

        # 指標計算
        with st.spinner("指標計算中..."):

            df = add_indicators(df)

        # スコア計算
        with st.spinner("スコア計算中..."):

            score, label, detail = score_latest(df)

        # =====================
        # 表示
        # =====================

        col1, col2 = st.columns(2)

        with col1:

            st.subheader(f"総合スコア：{score} / 20")

            st.subheader(label)

            st.write("### スコア内訳")

            st.json(detail)

        with col2:

            st.write("### 株価チャート")

            st.line_chart(df["Close"])

        st.write("### 最新データ")

        st.dataframe(df.tail(10))

    except Exception as e:

        st.error("エラーが発生しました")

        st.exception(e)
