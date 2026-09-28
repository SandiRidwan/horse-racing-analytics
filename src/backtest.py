"""
backtest.py — Strategi value betting & backtest ROI.

DASAR KONSEP:
  Pasar (odds) memberi "implied probability" = 1/odds (plus margin bookmaker).
  Model kita memberi pred_prob. Bila pred_prob > implied_prob, itu VALUE BET
  (taruhan bernilai harapan positif).

CONTOH: odds 5.0 -> implied 20%. Model bilang 28%. Edge +8% -> taruhan.

BACKTEST:
  - Untuk tiap taruhan, profit = (odds-1) bila menang, -1 bila kalah.
  - Ukur: total ROI, jumlah taruhan, win rate, drawdown, Sharpe-like.
  - Bandingkan strategi: taruhan semua favorit (baseline), model semua,
    model dengan ambang edge tertentu.

Ini backtest JUJUR: pakai race yang sudah selesai + odds yang tercatat.

Jalankan: python src/backtest.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
TABLES = ROOT / "reports" / "tables"
TABLES.mkdir(parents=True, exist_ok=True)


def load_bets():
    """Ambil data dengan odds + hasil + prediksi."""
    df = pd.read_csv(PROC / "predictions.csv")
    df = df[df["best_win_odds"].notna() & df["won"].notna()].copy()
    df["odds"] = pd.to_numeric(df["best_win_odds"], errors="coerce")
    df["implied_prob"] = 1 / df["odds"]
    df["edge"] = df["pred_prob"] - df["implied_prob"]
    df["won"] = df["won"].astype(int)
    return df


def simulate(bets: pd.DataFrame, stake=1.0):
    """Hitung hasil taruhan dengan stake datar."""
    if len(bets) == 0:
        return {"n_bets": 0, "roi_pct": 0.0, "profit": 0.0, "win_rate": 0.0,
                "avg_odds": 0.0}
    profit = np.where(bets["won"] == 1, (bets["odds"] - 1) * stake, -stake)
    total = profit.sum()
    staked = len(bets) * stake
    return {
        "n_bets": int(len(bets)),
        "profit": round(float(total), 2),
        "staked": round(staked, 2),
        "roi_pct": round(float(total / staked * 100), 2),
        "win_rate": round(float(bets["won"].mean() * 100), 1),
        "avg_odds": round(float(bets["odds"].mean()), 2),
    }


def equity_curve(bets: pd.DataFrame, stake=1.0):
    if len(bets) == 0:
        return pd.Series(dtype=float)
    profit = np.where(bets["won"] == 1, (bets["odds"] - 1) * stake, -stake)
    return pd.Series(np.cumsum(profit))


def run():
    df = load_bets()
    print(f"race dengan odds + hasil: {len(df)} kuda, "
          f"{df.groupby(['track','race_number']).ngroups} races")

    strategies = {}
    # baseline: taruh semua favorit (odds terendah per race)
    fav = df.loc[df.groupby(["track", "race_number"])["odds"].idxmin()]
    strategies["Semua favorit (baseline)"] = simulate(fav)

    # model: pilih kuda dengan pred_prob tertinggi per race
    top = df.loc[df.groupby(["track", "race_number"])["pred_prob"].idxmax()]
    strategies["Pilihan model (top-1)"] = simulate(top)

    # value: taruh bila edge > ambang
    for thr in [0.0, 0.05, 0.10, 0.15]:
        vb = df[df["edge"] > thr]
        strategies[f"Value bet (edge > {thr:.0%})"] = simulate(vb)

    res = pd.DataFrame(strategies).T
    print("\n=== HASIL BACKTEST ===")
    print(res.to_string())

    # equity curve strategi terbaik (edge>0.05)
    vb = df[df["edge"] > 0.05].sort_values(["track", "race_number"])
    eq = equity_curve(vb)
    eq.to_csv(TABLES / "equity_curve.csv", index=False)

    # top value bets
    top_vb = df.sort_values("edge", ascending=False).head(20)
    top_vb[["track", "race_number", "horse", "odds", "implied_prob",
             "pred_prob", "edge", "won"]].to_csv(
        TABLES / "top_value_bets.csv", index=False)

    res.to_csv(TABLES / "backtest_summary.csv")
    (PROC / "backtest.json").write_text(json.dumps(
        {k: v for k, v in strategies.items()}, indent=2))

    print("\n[OK] backtest_summary.csv, equity_curve.csv, top_value_bets.csv")
    return res


if __name__ == "__main__":
    run()
