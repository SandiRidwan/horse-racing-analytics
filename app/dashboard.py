"""
Horse Racing Analytics — Interactive Dashboard (Streamlit)
==========================================================
Prediksi & value-betting atas data balap Australia (Racenet).

Jalankan: streamlit run app/dashboard.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
TABLES = ROOT / "reports" / "tables"

C = {"p": "#1F5C3D", "a": "#E4A11B", "d": "#1B2A33", "g": "#8B9AA6",
     "r": "#C0392B", "b": "#2E6F95"}

st.set_page_config(page_title="Horse Racing Analytics", page_icon="🏇",
                   layout="wide", initial_sidebar_state="expanded")


@st.cache_data(show_spinner="Memuat data balap...")
def load():
    pred = pd.read_csv(PROC / "predictions.csv")
    metrics = json.loads((PROC / "metrics.json").read_text())
    bt = pd.read_csv(TABLES / "backtest_summary.csv", index_col=0)
    return pred, metrics, bt


def style(fig, h=430):
    fig.update_layout(
        height=h, margin=dict(l=10, r=10, t=54, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#D5DBE1"),
        title=dict(font=dict(size=16, color="#fff")),
        legend=dict(bgcolor="rgba(0,0,0,0)"))
    fig.update_xaxes(gridcolor="#2A3038", zeroline=False)
    fig.update_yaxes(gridcolor="#2A3038", zeroline=False)
    return fig


def kpi(col, label, value, sub, color):
    col.markdown(
        f"""<div style="background:#1A1F2B;border-left:4px solid {color};
        padding:14px 16px;border-radius:10px;height:112px;">
        <div style="color:#9AA7B4;font-size:.76rem;text-transform:uppercase;
        letter-spacing:.06em;">{label}</div>
        <div style="color:{color};font-size:1.7rem;font-weight:700;
        margin-top:6px;">{value}</div>
        <div style="color:#6B7885;font-size:.75rem;">{sub}</div></div>""",
        unsafe_allow_html=True)


pred, metrics, bt = load()

st.sidebar.markdown("### 🎛️ Controls")
tracks = sorted(pred["track"].dropna().unique())
sel_tracks = st.sidebar.multiselect("Tracks", tracks, default=tracks[:8])
only_odds = st.sidebar.toggle("Hanya yang punya odds", value=True)
st.sidebar.markdown("---")
st.sidebar.caption("Sumber: Racenet (racenet.com.au) · diambil zero-browser "
                   "(curl_cffi + proxy AU + decode Nuxt SSR state).")

st.markdown(
    f"""<div style="background:linear-gradient(100deg,{C['p']},{C['b']});
    padding:22px 26px;border-radius:14px;margin-bottom:18px;">
    <div style="font-size:1.7rem;font-weight:800;color:white;">
    🏇 Horse Racing Analytics</div>
    <div style="color:#D7E4DC;font-size:.9rem;margin-top:4px;">
    Prediksi pemenang & value-betting · data Racenet (Australia) ·
    by <b>Sandi Ridwan</b></div></div>""",
    unsafe_allow_html=True)

df = pred.copy()
if sel_tracks:
    df = df[df["track"].isin(sel_tracks)]
if only_odds:
    df = df[df["best_win_odds"].notna()]

k1, k2, k3, k4, k5 = st.columns(5)
kpi(k1, "Kenalan kuda", f"{len(df):,}", "pada data terfilter", C["p"])
kpi(k2, "ROC-AUC", f"{metrics['roc_auc']:.3f}", "0.5=acak · 1.0=sempurna", C["b"])
kpi(k3, "Top-pick acc", f"{metrics['top_pick_acc']*100:.1f}%",
    "vs acak ~12%", C["a"])
kpi(k4, "Brier", f"{metrics['brier']:.3f}", "makin kecil makin baik", C["r"])
kpi(k5, "Races (test)", f"{metrics['n_races_test']}", "evaluasi hold-out", C["d"])
st.write("")

t1, t2, t3, t4 = st.tabs(["🎯 Predictions", "📊 Model", "💰 Backtest", "📈 Racing"])

with t1:
    st.markdown("#### Prediksi pemenang per race")
    races = (df.groupby(["track", "race_number"])["pred_prob"].max()
             .reset_index().head(60))
    pick = st.selectbox(
        "Pilih race",
        [f"{r.track} · Race {int(r.race_number)}" for r in races.itertuples()])
    if pick:
        tr, rn = pick.split(" · Race ")
        sub = df[(df["track"] == tr) & (df["race_number"] == int(rn))]
        sub = sub.sort_values("pred_prob", ascending=False)
        fig = px.bar(sub, x="pred_prob", y="horse", orientation="h",
                     color="pred_prob", color_continuous_scale="Greens",
                     hover_data=["best_win_odds", "implied_prob", "barrier"])
        fig.update_traces(texttemplate="%{x:.1%}", textposition="outside")
        style(fig, 420).update_layout(coloraxis_showscale=False,
                                      title=f"{tr} — Race {rn}: probabilitas menang")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(
            sub[["horse", "number", "barrier", "best_win_odds", "implied_prob",
                 "pred_prob", "won", "finish_position"]],
            use_container_width=True, hide_index=True)

with t2:
    c1, c2 = st.columns(2)
    with c1:
        coef = pd.Series(metrics["coef"]).sort_values()
        fig = px.bar(x=coef.values, y=coef.index, orientation="h",
                     color=coef.values, color_continuous_scale="RdYlGn")
        style(fig, 520).update_layout(coloraxis_showscale=False,
                                      title="Kepentingan fitur (koefisien)")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        cal = pd.read_csv(TABLES / "calibration.csv")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines",
                                 name="Sempurna", line=dict(dash="dash",
                                                            color=C["g"])))
        fig.add_trace(go.Scatter(x=cal["mean_pred"], y=cal["actual"],
                                 mode="lines+markers", name="Model",
                                 line=dict(color=C["p"], width=2.5)))
        style(fig, 520).update_layout(title="Calibration",
                                      xaxis_title="Predicted",
                                      yaxis_title="Actual")
        st.plotly_chart(fig, use_container_width=True)

with t3:
    st.markdown("#### Backtest strategi taruhan")
    show = bt.copy()
    show["n_bets"] = show["n_bets"].astype(int)
    st.dataframe(show, use_container_width=True)
    fig = px.bar(x=bt["roi_pct"], y=bt.index, orientation="h",
                 color=bt["roi_pct"], color_continuous_scale="RdYlGn",
                 labels={"x": "ROI (%)", "y": ""})
    style(fig, 420).update_layout(coloraxis_showscale=False,
                                  title="ROI per strategi (0% = impas)")
    st.plotly_chart(fig, use_container_width=True)
    st.info("⚠️ Semua strategi masih negatif karena margin bookmaker & sampel "
            "kecil. Yang penting: model (−4.9%) jauh mengalahkan baseline "
            "favorit (−36.5%). Kejujuran ini bagian dari analisis.")

with t4:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Win rate per bucket odds")
        d = df[df["best_win_odds"].notna() & df["won"].notna()].copy()
        d["odds"] = pd.to_numeric(d["best_win_odds"], errors="coerce")
        d["bucket"] = pd.cut(d["odds"], [0, 2, 4, 6, 10, 20, 1000],
                             labels=["1-2", "2-4", "4-6", "6-10", "10-20", "20+"])
        g = d.groupby("bucket", observed=True)["won"].agg(["mean", "size"]).reset_index()
        fig = px.bar(g, x="bucket", y="mean", text="size",
                     color="mean", color_continuous_scale="Blues")
        fig.update_traces(texttemplate="n=%{text}", textposition="outside")
        style(fig, 420).update_layout(coloraxis_showscale=False,
                                      title="Win rate vs odds",
                                      yaxis_title="win rate")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown("##### Win rate per barrier")
        d = df[df["barrier"].notna() & df["won"].notna()].copy()
        d["barrier"] = pd.to_numeric(d["barrier"], errors="coerce")
        d = d[d["barrier"] <= 12]
        g = d.groupby("barrier")["won"].agg(["mean", "size"]).reset_index()
        fig = px.bar(g, x="barrier", y="mean", text="size",
                     color="mean", color_continuous_scale="Oranges")
        fig.update_traces(texttemplate="n=%{text}", textposition="outside")
        style(fig, 420).update_layout(coloraxis_showscale=False,
                                      title="Win rate vs barrier",
                                      yaxis_title="win rate")
        st.plotly_chart(fig, use_container_width=True)

st.markdown(
    f"""<hr style="border-color:#2A3038;">
    <div style="color:{C['g']};font-size:.8rem;text-align:center;">
    🏇 Horse Racing Analytics · data Racenet · model logistic regression
    (numpy) · backtest jujur · by <b>Sandi Ridwan</b><br>
    ⚠️ Bukan saran taruhan. Analisis edukasional; pertaruhan punya risiko.</div>""",
    unsafe_allow_html=True)
