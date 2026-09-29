"""
Horse Racing Analytics — Interactive Dashboard (Streamlit)
==========================================================
Prediksi & value-betting atas data balap Australia (Racenet).

Jalankan: streamlit run app/dashboard.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
TABLES = ROOT / "reports" / "tables"
sys.path.insert(0, str(ROOT / "src"))
import explanations as X  # noqa: E402
import insights_content  # noqa: E402,F401
import insight as INS  # noqa: E402
import echarts_charts as EC  # noqa: E402  (boxplot, waterfall)

C = {"p": "#1F5C3D", "a": "#E4A11B", "d": "#1B2A33", "g": "#8B9AA6",
     "r": "#C0392B", "b": "#2E6F95"}

st.set_page_config(page_title="Horse Racing Analytics", page_icon="🏇",
                   layout="wide", initial_sidebar_state="expanded")


@st.cache_data(show_spinner="Memuat data balap...")
def load():
    pred = pd.read_csv(PROC / "predictions_v2.csv")
    metrics = json.loads((PROC / "metrics_v2.json").read_text())
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
    df = df[df["best_odds"].notna()]

k1, k2, k3, k4, k5 = st.columns(5)
kpi(k1, "Kenalan kuda", f"{len(df):,}", "pada data terfilter", C["p"])
_ens = metrics.get("models", {}).get("Ensemble", {})
_auc = _ens.get("roc_auc", metrics.get("roc_auc", 0))
_brier = _ens.get("brier", metrics.get("brier", 0))
_t3 = _ens.get("top3", metrics.get("top3", 0))
kpi(k2, "ROC-AUC", f"{_auc:.3f}", "5-fold CV · 0.5=acak", C["b"])
kpi(k3, "Top-3 acc", f"{_t3*100:.1f}%", "ensemble (CV)", C["a"])
kpi(k4, "Brier", f"{_brier:.3f}", "makin kecil makin baik", C["r"])
kpi(k5, "Races (CV)", f"{metrics.get('n_races','-')}", "5-fold cross-val", C["d"])
st.write("")

t1, t2, t3, t4 = st.tabs(["🎯 Predictions", "📊 Model", "💰 Backtest", "📈 Racing"])

with t1:
    X.render("predictions", st=st)
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
                     hover_data=["best_odds", "implied_prob", "barrier"])
        fig.update_traces(texttemplate="%{x:.1%}", textposition="outside")
        style(fig, 420).update_layout(coloraxis_showscale=False,
                                      title=f"{tr} — Race {rn}: probabilitas menang")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(
            sub[["horse", "number", "barrier", "best_odds", "implied_prob",
                 "pred_prob", "won", "finish_position"]],
            use_container_width=True, hide_index=True)
        INS.box("predictions", st=st)

    st.markdown("#### Sebaran probabilitas prediksi per track (boxplot ECharts)")
    st.caption("Boxplot per track memperlihatkan **kepercayaan model**: kotak "
               "rendah & sempit = field merata (model ragu), kotak tinggi = ada "
               "kuda favorit kuat. Titik = kuda dengan prediksi ekstrem.")
    try:
        _tp = (df.groupby("track")["pred_prob"].apply(list))
        _tp = _tp[_tp.map(len) >= 4].head(14)
        if len(_tp):
            EC.boxplot(
                categories=[str(k)[:16] for k in _tp.index],
                values=[list(v) for v in _tp.values],
                title="Sebaran pred_prob per track", yname="probabilitas menang",
                height=460)
    except Exception as _e:  # noqa: BLE001
        st.caption(f"boxplot tak tersedia ({_e}).")
    INS.box("predictions", st=st)

with t2:
    X.render("feature_importance", st=st)
    X.render("calibration", st=st)
    c1, c2 = st.columns(2)
    with c1:
        coef = pd.Series(metrics.get("coef") or {}).sort_values().tail(14)
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
    INS.box("feature_importance", st=st)
    INS.box("calibration", st=st)

with t3:
    X.render("backtest", st=st)
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
    INS.box("backtest", st=st)

    st.markdown("#### Jembatan ROI: favorit → model (waterfall ECharts)")
    st.caption("Waterfall menjembatani **ROI baseline 'taruhan favorit'** ke "
               "**ROI 'pilihan model'**: bar merah = titik awal negatif, bar "
               "hijau = perbaikan dari strategi model, bar biru = hasil akhir. "
               "Menunjukkan seberapa besar nilai tambah seleksi model.")
    try:
        _roi = bt["roi_pct"].to_dict()
        _fav = _mdl = None
        for k in _roi:
            kl = str(k).lower()
            if _fav is None and ("favorit" in kl or "favorite" in kl or "baseline" in kl):
                _fav = float(_roi[k])
            if _mdl is None and ("model" in kl):
                _mdl = float(_roi[k])
        if _fav is not None and _mdl is not None:
            EC.waterfall(
                categories=["Favorit (baseline)", "Keunggulan model",
                            "Model (top-1)"],
                values=[_fav, (_mdl - _fav), 0.0],
                title="Dekomposisi ROI (%)", yname="ROI (%)", height=440)
        else:
            st.caption("Waterfall butuh strategi 'favorit' & 'model' di backtest.")
    except Exception as _e:  # noqa: BLE001
        st.caption(f"waterfall tak tersedia ({_e}).")
    INS.box("backtest", st=st)

with t4:
    c1, c2 = st.columns(2)
    with c1:
        X.render("odds_winrate", st=st)
        d = df[df["best_odds"].notna() & df["won"].notna()].copy()
        d["odds"] = pd.to_numeric(d["best_odds"], errors="coerce")
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
        INS.box("odds_winrate", st=st)
    with c2:
        X.render("barrier", st=st)
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
        INS.box("barrier", st=st)

st.markdown(
    f"""<hr style="border-color:#2A3038;">
    <div style="color:{C['g']};font-size:.8rem;text-align:center;">
    🏇 Horse Racing Analytics · data Racenet · model logistic regression
    (numpy) · backtest jujur · by <b>Sandi Ridwan</b><br>
    ⚠️ Bukan saran taruhan. Analisis edukasional; pertaruhan punya risiko.</div>""",
    unsafe_allow_html=True)
