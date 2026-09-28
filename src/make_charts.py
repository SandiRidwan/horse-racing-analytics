"""make_charts.py — visualisasi analisis balap kuda + model."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
FIG = ROOT / "reports" / "figures"
TABLES = ROOT / "reports" / "tables"
FIG.mkdir(parents=True, exist_ok=True)

C = {"p": "#1F5C3D", "a": "#E4A11B", "d": "#1B2A33", "g": "#8B9AA6",
     "r": "#C0392B", "b": "#2E6F95"}

plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 130, "font.size": 10,
    "axes.titlesize": 12, "axes.titleweight": "bold",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#CCCCCC", "axes.grid": True, "grid.color": "#EEEEEE",
    "figure.facecolor": "white",
})


def _save(fig, name):
    fp = FIG / f"{name}.png"
    fig.tight_layout()
    fig.savefig(fp, bbox_inches="tight")
    plt.close(fig)
    print(f"  [fig] {fp.name}")


def chart_odds_vs_win():
    df = pd.read_csv(PROC / "predictions.csv")
    df = df[df["best_win_odds"].notna() & df["won"].notna()].copy()
    odds = pd.to_numeric(df["best_win_odds"], errors="coerce")
    df = df.assign(odds=odds)
    bins = [0, 2, 4, 6, 10, 20, 1000]
    labels = ["1-2", "2-4", "4-6", "6-10", "10-20", "20+"]
    df["bucket"] = pd.cut(df["odds"], bins=bins, labels=labels)
    g = df.groupby("bucket", observed=True).agg(
        n=("won", "size"), win=("won", "mean"))
    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(g))
    mid_odds = [1.5, 3, 5, 8, 15, 30][:len(g)]
    implied = [100 / o for o in mid_odds]
    ax.bar(x, g["win"] * 100, color=C["b"], zorder=3)
    ax2 = ax.twinx()
    ax2.plot(x, implied, "o--", color=C["a"], label="implied prob (mid-odds)")
    ax2.set_ylabel("Implied probability (%)", color=C["a"])
    ax2.tick_params(axis="y", labelcolor=C["a"])
    ax2.grid(False)
    for i, (n, w) in enumerate(zip(g["n"], g["win"])):
        ax.text(i, w * 100 + 1, f"{w*100:.0f}%\n(n={n})", ha="center", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels(labels[:len(g)])
    ax.set_xlabel("Odds bucket"); ax.set_ylabel("Actual win rate (%)", color=C["b"])
    ax.set_title("Win Rate by Odds Bucket\n(favorit menang lebih sering, spt diharapkan)")
    ax.grid(axis="x", visible=False)
    _save(fig, "01_winrate_by_odds")


def chart_calibration():
    p = TABLES / "calibration.csv"
    if not p.exists():
        return
    cal = pd.read_csv(p)
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.plot([0, 1], [0, 1], "--", color=C["g"], label="Sempurna")
    ax.plot(cal["mean_pred"], cal["actual"], "o-", color=C["p"],
            ms=8, lw=2, label="Model")
    for _, r in cal.iterrows():
        ax.annotate(f"n={r['n']}", (r["mean_pred"], r["actual"]),
                    textcoords="offset points", xytext=(6, 6), fontsize=8)
    ax.set_xlabel("Predicted probability")
    ax.set_ylabel("Actual win rate")
    ax.set_title("Calibration Plot\n(model mendekati diagonal = terkalibrasi)")
    ax.legend(frameon=False)
    _save(fig, "02_calibration")


def chart_feature_importance():
    m = json.loads((PROC / "metrics.json").read_text())
    coef = m["coef"]
    items = sorted(coef.items(), key=lambda x: abs(x[1]))[-12:]
    fig, ax = plt.subplots(figsize=(9, 6))
    names = [k for k, _ in items]
    vals = [v for _, v in items]
    colors = [C["p"] if v > 0 else C["r"] for v in vals]
    ax.barh(names, vals, color=colors, zorder=3)
    ax.axvline(0, color=C["d"], lw=1)
    ax.set_xlabel("Coefficient (positif = naikkan peluang menang)")
    ax.set_title("Feature Importance (Logistic Regression)")
    ax.grid(axis="y", visible=False)
    _save(fig, "03_feature_importance")


def chart_backtest():
    p = TABLES / "backtest_summary.csv"
    if not p.exists():
        return
    bt = pd.read_csv(p, index_col=0)
    fig, ax = plt.subplots(figsize=(9, 5.5))
    b = bt.iloc[::-1]
    colors = [C["p"] if v == bt["roi_pct"].max() else
              (C["r"] if v < 0 else C["g"]) for v in b["roi_pct"]]
    bars = ax.barh(b.index, b["roi_pct"], color=colors, zorder=3)
    for bar, (_, r) in zip(bars, b.iterrows()):
        ax.text(r["roi_pct"] + (0.5 if r["roi_pct"] > 0 else -0.5),
                bar.get_y() + bar.get_height() / 2,
                f"{r['roi_pct']:.1f}%  (n={int(r['n_bets'])})",
                va="center", ha="left" if r["roi_pct"] > 0 else "right",
                fontsize=8, color=C["d"])
    ax.axvline(0, color=C["d"], lw=1)
    ax.set_xlabel("ROI (%)")
    ax.set_title("Backtest: ROI per Strategy\n(break-even = 0%; bookmaker margin membuat semua negatif)")
    ax.grid(axis="y", visible=False)
    _save(fig, "04_backtest_roi")


def chart_equity():
    p = TABLES / "equity_curve.csv"
    if not p.exists():
        return
    _df = pd.read_csv(p)
    eq = _df.iloc[:, -1]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(range(len(eq)), eq.values, color=C["p"], lw=2)
    ax.axhline(0, color=C["g"], ls="--")
    ax.fill_between(range(len(eq)), eq.values, 0,
                    where=(eq.values >= 0), color=C["p"], alpha=0.15)
    ax.fill_between(range(len(eq)), eq.values, 0,
                    where=(eq.values < 0), color=C["r"], alpha=0.15)
    ax.set_xlabel("Bet number"); ax.set_ylabel("Cumulative profit (units)")
    ax.set_title("Equity Curve — Value Bet (edge > 5%)")
    _save(fig, "05_equity_curve")


def chart_winners_by_barrier():
    df = pd.read_csv(PROC / "predictions.csv")
    df = df[df["barrier"].notna() & df["won"].notna()].copy()
    df["barrier"] = pd.to_numeric(df["barrier"], errors="coerce")
    df = df[df["barrier"] <= 12]
    g = df.groupby("barrier").agg(n=("won", "size"), win=("won", "mean"))
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(g.index, g["win"] * 100, color=C["b"], zorder=3)
    for i, (n, w) in zip(g.index, zip(g["n"], g["win"])):
        ax.text(i, w * 100 + 0.3, f"n={n}", ha="center", fontsize=7)
    ax.set_xlabel("Barrier (starting gate)"); ax.set_ylabel("Win rate (%)")
    ax.set_title("Win Rate by Barrier Position")
    ax.set_xticks(g.index)
    _save(fig, "06_barrier_winrate")


if __name__ == "__main__":
    print("Membuat visualisasi...")
    chart_odds_vs_win()
    chart_calibration()
    chart_feature_importance()
    chart_backtest()
    chart_equity()
    chart_winners_by_barrier()
    print(f"[OK] {FIG}")
