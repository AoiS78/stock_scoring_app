import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

st.set_page_config(
    page_title="株スコアリング",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# CSS
st.markdown("""
<style>
    .main { padding: 0.5rem; }
    .block-container { padding: 1rem 0.8rem; max-width: 480px; margin: auto; }
    h1 { font-size: 1.4rem !important; }
    h2 { font-size: 1.1rem !important; }
    h3 { font-size: 1rem !important; }
    .stSlider > div { padding: 0; }

    .score-box {
        border-radius: 16px;
        padding: 1.2rem;
        text-align: center;
        margin: 1rem 0;
        color: white;
        font-weight: bold;
    }
    .score-number { font-size: 3rem; line-height: 1; }
    .score-label { font-size: 1.2rem; margin-top: 0.4rem; }
    .score-action { font-size: 1.5rem; margin-top: 0.3rem; }

    .cat-header {
        background: #1e1e2e;
        border-radius: 10px;
        padding: 0.5rem 0.8rem;
        margin: 0.8rem 0 0.3rem 0;
        font-weight: bold;
        font-size: 0.95rem;
    }
    .metric-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.4rem 0.2rem;
        border-bottom: 1px solid #2d2d2d;
        font-size: 0.85rem;
    }
    .badge {
        border-radius: 8px;
        padding: 2px 10px;
        font-weight: bold;
        font-size: 0.8rem;
    }
    .badge-on  { background:#1a472a; color:#4ade80; }
    .badge-off { background:#2d2d2d; color:#888; }

    .history-card {
        background: #1a1a2e;
        border-radius: 12px;
        padding: 0.8rem;
        margin: 0.5rem 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    div[data-testid="stForm"] { border: none; padding: 0; }
    .stButton > button {
        width: 100%;
        border-radius: 12px;
        height: 3rem;
        font-size: 1rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ─── 状態初期化 ───────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []

# ─── スコア定義 ───────────────────────────────────────────
CRITERIA = {
    "trend": {
        "label": "📈 トレンド系",
        "max": 8,
        "items": [
            {"key": "above_200ma",  "label": "株価 > 200日MA",                   "points": 3},
            {"key": "golden_cross", "label": "50日MA > 200日MA（GC状態）",        "points": 2},
            {"key": "above_50ma",   "label": "株価 > 50日MA",                    "points": 2},
            {"key": "near_52w_high","label": "52週高値の80%以上",                 "points": 1},
        ]
    },
    "momentum": {
        "label": "⚡ モメンタム系",
        "max": 6,
        "items": [
            {"key": "rsi_50_70",    "label": "RSI 50〜70（健全な上昇）",          "points": 3},
            {"key": "rsi_40_50",    "label": "RSI 40〜50（押し目圏）",            "points": 1},
            {"key": "rsi_under30",  "label": "RSI 30以下（売られすぎ）",          "points": 2},
            {"key": "macd_positive","label": "MACDヒストグラム プラス圏",         "points": 2},
            {"key": "macd_cross",   "label": "MACDヒストグラム マイナス→プラス転換","points": 1},
        ]
    },
    "value": {
        "label": "💡 出来高・バリュー系",
        "max": 6,
        "items": [
            {"key": "volume_surge", "label": "出来高 > 20日平均×1.5（上昇時）",  "points": 2},
            {"key": "bb_normal",    "label": "BB -1σ〜+1σ 内（過熱なし）",       "points": 1},
            {"key": "fair_price",   "label": "52週平均乖離 -10%〜+10%",           "points": 1},
            {"key": "rs_strong",    "label": "S&P500より相対強度が高い（3ヶ月）", "points": 2},
        ]
    }
}

JUDGEMENTS = [
    (16, 20, "#16a34a", "🔥 強い買い",  "強いシグナル。積極的に買い"),
    (12, 15, "#22c55e", "✅ 買い",      "買いシグナル。エントリー検討"),
    ( 8, 11, "#eab308", "⏸️ 静観",      "動かない。様子見"),
    ( 4,  7, "#f97316", "⚠️ 売り検討",  "一部利確 or 損切り準備"),
    ( 0,  3, "#ef4444", "❌ 売り",      "撤退。キャッシュに戻す"),
]

def get_judgement(score):
    for lo, hi, color, action, note in JUDGEMENTS:
        if lo <= score <= hi:
            return color, action, note
    return "#888", "—", "—"

# ─── UI ─────────────────────────────────────────────────
st.markdown("## 📊 株スコアリング")
st.caption("長期・中リスク・米国株向け定量判断システム")

ticker = st.text_input("銘柄ティッカー（任意）", placeholder="例: AAPL, NVDA, TSLA").upper()

tab1, tab2 = st.tabs(["📝 採点", "📜 履歴"])

# ══════════════════════════════════
# TAB 1: 採点
# ══════════════════════════════════
with tab1:
    checked = {}
    total = 0

    for cat_key, cat in CRITERIA.items():
        st.markdown(f'<div class="cat-header">{cat["label"]}　<span style="color:#888;font-size:0.8rem;">最大{cat["max"]}点</span></div>', unsafe_allow_html=True)
        for item in cat["items"]:
            col1, col2 = st.columns([5, 1])
            with col1:
                val = st.checkbox(f'{item["label"]}　+{item["points"]}点', key=item["key"])
            checked[item["key"]] = val
            if val:
                total += item["points"]

    # スコア表示
    color, action, note = get_judgement(total)
    st.markdown(f"""
    <div class="score-box" style="background:{color};">
        <div class="score-number">{total}<span style="font-size:1.2rem;">/20</span></div>
        <div class="score-action">{action}</div>
        <div class="score-label" style="opacity:0.9;">{note}</div>
    </div>
    """, unsafe_allow_html=True)

    # ゲージ
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=total,
        gauge={
            "axis": {"range": [0, 20], "tickwidth": 1, "tickcolor": "white"},
            "bar": {"color": color},
            "bgcolor": "#1e1e2e",
            "steps": [
                {"range": [0,  3], "color": "#3d0000"},
                {"range": [3,  7], "color": "#4a1500"},
                {"range": [7, 11], "color": "#3d3000"},
                {"range": [11,15], "color": "#003d10"},
                {"range": [15,20], "color": "#004d15"},
            ],
            "threshold": {"line": {"color": "white", "width": 3}, "thickness": 0.75, "value": total}
        },
        number={"font": {"color": "white", "size": 48}},
        domain={"x": [0, 1], "y": [0, 1]}
    ))
    fig.update_layout(
        height=200, margin=dict(t=20, b=0, l=20, r=20),
        paper_bgcolor="#0e0e1a", font_color="white"
    )
    st.plotly_chart(fig, use_container_width=True)

    # 判定表
    with st.expander("📋 判定基準を見る"):
        for lo, hi, c, act, note2 in JUDGEMENTS:
            st.markdown(f'<div style="padding:4px 0;font-size:0.85rem;"><span style="color:{c};font-weight:bold;">{act}</span>　{lo}〜{hi}点　<span style="color:#888;">{note2}</span></div>', unsafe_allow_html=True)

    # 保存ボタン
    if st.button("💾 このスコアを保存", type="primary"):
        entry = {
            "date": datetime.now().strftime("%m/%d %H:%M"),
            "ticker": ticker if ticker else "—",
            "score": total,
            "action": action,
            "color": color,
            "checks": {k: v for k, v in checked.items() if v}
        }
        st.session_state.history.insert(0, entry)
        st.success(f"保存しました！ {ticker or ''} {total}点 {action}")

# ══════════════════════════════════
# TAB 2: 履歴
# ══════════════════════════════════
with tab2:
    if not st.session_state.history:
        st.info("まだ履歴がありません。\n採点タブでスコアを保存してください。")
    else:
        # スコア推移チャート
        if len(st.session_state.history) >= 2:
            df = pd.DataFrame(st.session_state.history[::-1])
            fig2 = px.line(
                df, x="date", y="score",
                markers=True, color_discrete_sequence=["#22c55e"],
                labels={"date": "", "score": "スコア"},
                title="スコア推移"
            )
            fig2.add_hrect(y0=16, y1=20, fillcolor="#16a34a", opacity=0.15, line_width=0)
            fig2.add_hrect(y0=12, y1=16, fillcolor="#22c55e", opacity=0.1,  line_width=0)
            fig2.add_hrect(y0=8,  y1=11, fillcolor="#eab308", opacity=0.1,  line_width=0)
            fig2.add_hrect(y0=4,  y1=7,  fillcolor="#f97316", opacity=0.1,  line_width=0)
            fig2.add_hrect(y0=0,  y1=3,  fillcolor="#ef4444", opacity=0.1,  line_width=0)
            fig2.update_layout(
                height=220, paper_bgcolor="#0e0e1a", plot_bgcolor="#0e0e1a",
                font_color="white", margin=dict(t=40, b=20, l=10, r=10),
                yaxis=dict(range=[0, 20], gridcolor="#2d2d2d"),
                xaxis=dict(gridcolor="#2d2d2d")
            )
            st.plotly_chart(fig2, use_container_width=True)

        # 履歴カード
        for i, entry in enumerate(st.session_state.history):
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.markdown(f"**{entry['ticker']}**　{entry['date']}")
                st.caption(entry['action'])
            with col2:
                st.markdown(f'<span style="color:{entry["color"]};font-size:1.5rem;font-weight:bold;">{entry["score"]}点</span>', unsafe_allow_html=True)
            with col3:
                if st.button("🗑", key=f"del_{i}"):
                    st.session_state.history.pop(i)
                    st.rerun()
            st.divider()

        if st.button("🗑️ 履歴を全削除"):
            st.session_state.history = []
            st.rerun()
