"""
model.py — Model prediksi pemenang balap (fitur kaya + odds).

Dataset: data/processed/features_raw.csv
  - 387 baris dengan fitur lengkap + odds + hasil (untuk training/eval)
  - 694 baris dengan odds (termasuk race mendatang -> untuk prediksi)

Fitur:
  pasar/odds : implied_prob (dari best_win_odds), fluc_move
  performa   : win_pct, place_pct, roi, career_winrate, days_since_last_run,
               last_run_finish, last_run_sp
  struktur   : barrier, number, weight, age
  koneksi    : trainer_jockey_win
  konteks    : distance, starters, prize_money

Model: logistic regression (numpy) + normalisasi per-race.
Evaluasi: Brier, log loss, ROC-AUC, top-pick accuracy, calibration.

Jalankan: python src/model.py
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

FEATURES = [
    "implied_prob",          # 1/odds (pasar) - prediktor terkuat di betting
    "log_odds",
    "fluc_move",             # pergerakan odds (market momentum)
    "win_pct", "place_pct", "roi", "career_winrate",
    "days_since_last_run", "last_run_finish", "last_run_sp",
    "barrier", "number", "weight", "age",
    "trainer_jockey_win",
    "distance", "starters", "prize_per_starter",
]


def load_features() -> pd.DataFrame:
    df = pd.read_csv(PROC / "features_raw.csv")
    # fitur turunan
    odds = pd.to_numeric(df["best_win_odds"], errors="coerce")
    df["implied_prob"] = 1 / odds
    df["log_odds"] = np.log(odds)
    fo = pd.to_numeric(df["fluc_open"], errors="coerce")
    fl = pd.to_numeric(df["fluc_last"], errors="coerce")
    df["fluc_move"] = ((fl - fo) / fo).replace([np.inf, -np.inf], np.nan)
    pm = pd.to_numeric(df["prize_money"], errors="coerce")
    st = pd.to_numeric(df["starters"], errors="coerce")
    df["prize_per_starter"] = pm / st
    df["won"] = pd.to_numeric(df["won"], errors="coerce")
    return df


def _matrix(df):
    d = df.copy()
    for c in FEATURES:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    # imputasi median (agar baris tidak hilang) + mask yang valid
    d = d.dropna(subset=["won"])
    for c in FEATURES:
        d[c] = d[c].fillna(d[c].median())
    X = d[FEATURES].to_numpy(float)
    y = d["won"].to_numpy(float)
    return d, X, y


def _std(X, mu=None, sd=None):
    if mu is None:
        mu, sd = X.mean(0), X.std(0) + 1e-9
    return (X - mu) / sd, mu, sd


def train_logreg(X, y, epochs=2000, lr=0.05, l2=1e-3):
    n, p = X.shape
    w, b = np.zeros(p), 0.0
    for _ in range(epochs):
        pred = 1 / (1 + np.exp(-np.clip(X @ w + b, -30, 30)))
        w -= lr * (X.T @ (pred - y) / n + l2 * w)
        b -= lr * (pred - y).mean()
    return w, b


def predict(X, w, b):
    return 1 / (1 + np.exp(-np.clip(X @ w + b, -30, 30)))


def race_norm(df, p):
    d = df.copy()
    d["_p"] = p
    key = ["track", "race_number"]
    s = d.groupby(key)["_p"].transform("sum")
    n = d.groupby(key)["_p"].transform("size")
    return (d["_p"] / s.replace(0, np.nan)).fillna(1 / n).to_numpy()


def brier(y, p):
    return float(np.mean((p - y) ** 2))


def log_loss(y, p):
    p = np.clip(p, 1e-12, 1 - 1e-12)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def roc_auc(y, p):
    pos, neg = p[y == 1], p[y == 0]
    if not len(pos) or not len(neg):
        return float("nan")
    order = np.argsort(np.concatenate([pos, neg]))
    ranks = np.empty_like(order, float)
    ranks[order] = np.arange(1, len(order) + 1)
    return float((ranks[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) /
                 (len(pos) * len(neg)))


def calibration(y, p, bins=5):
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(p, edges) - 1, 0, bins - 1)
    rows = []
    for i in range(bins):
        m = idx == i
        if m.sum():
            rows.append({"bin": f"{edges[i]:.1f}-{edges[i+1]:.1f}",
                         "n": int(m.sum()),
                         "mean_pred": round(float(p[m].mean()), 3),
                         "actual": round(float(y[m].mean()), 3)})
    return pd.DataFrame(rows)


def top_pick(df, p):
    d = df.copy()
    d["_p"] = p
    key = ["track", "race_number"]
    hits = tot = 0
    for _, g in d.groupby(key):
        if len(g) < 2:
            continue
        tot += 1
        if g.loc[g["_p"].idxmax(), "won"] == 1:
            hits += 1
    return (hits / tot if tot else float("nan")), tot


def run():
    df = load_features()
    # hanya baris dengan hasil untuk training
    trainable = df[df["won"].notna()].copy()
    d, X, y = _matrix(trainable)
    print(f"training rows: {len(d)} | fits: {len(FEATURES)}")
    print(f"baseline won-rate: {y.mean()*100:.1f}%")

    # split per-race
    rng = np.random.default_rng(42)
    key = d["track"].astype(str) + "|" + d["race_number"].astype(str)
    races = key.unique()
    rng.shuffle(races)
    cut = int(len(races) * 0.7)
    tr_races = set(races[:cut])
    tr = key.isin(tr_races).to_numpy()
    Xtr, Xte, ytr, yte = X[tr], X[~tr], y[tr], y[~tr]
    dtr, dte = d[tr].reset_index(drop=True), d[~tr].reset_index(drop=True)

    Xtr_s, mu, sd = _std(Xtr)
    Xte_s, _, _ = _std(Xte, mu, sd)
    w, b = train_logreg(Xtr_s, ytr)
    p_te = race_norm(dte, predict(Xte_s, w, b))

    print(f"\ntrain {len(dtr)} | test {len(dte)}")
    print("\n=== METRIK (test) ===")
    print(f"  Brier     : {brier(yte, p_te):.4f}  (kecil = baik)")
    print(f"  Log loss  : {log_loss(yte, p_te):.4f}")
    print(f"  ROC-AUC   : {roc_auc(yte, p_te):.4f}  (0.5 acak, 1.0 sempurna)")
    acc, nr = top_pick(dte, p_te)
    base = 100 / max(1, dte.groupby(["track", "race_number"]).size().mean())
    print(f"  Top-pick  : {acc*100:.1f}%  vs acak {base:.1f}%  [{nr} races]")

    print("\n=== CALIBRATION ===")
    cal = calibration(yte, p_te, 5)
    print(cal.to_string(index=False))

    print("\n=== KEPENTINGAN FITUR ===")
    for f, wi in sorted(zip(FEATURES, w), key=lambda x: -abs(x[1]))[:12]:
        print(f"  {f:20} {wi:+.3f}")

    # === prediksi untuk SEMUA race (termasuk yang belum selesai) ===
    dall, Xall, _ = _matrix(df.assign(won=df["won"].fillna(0)))
    allp = race_norm(dall, predict(_std(Xall, mu, sd)[0], w, b))
    dall["pred_prob"] = allp
    dall["pred_rank"] = dall.groupby(["track", "race_number"])["pred_prob"].rank(ascending=False)
    dall.to_csv(PROC / "predictions.csv", index=False)

    # value bets: pred_prob vs implied_prob pasar
    vb = dall[dall["implied_prob"].notna()].copy()
    vb["edge"] = vb["pred_prob"] - vb["implied_prob"]
    vb = vb.sort_values("edge", ascending=False).head(25)
    vb[["track", "race_number", "horse", "best_win_odds", "implied_prob",
        "pred_prob", "edge", "won"]].to_csv(TABLES / "value_bets.csv", index=False)
    print(f"\n[OK] predictions.csv + value_bets.csv")

    metrics = {"brier": brier(yte, p_te), "log_loss": log_loss(yte, p_te),
               "roc_auc": roc_auc(yte, p_te), "top_pick_acc": acc,
               "n_train": len(dtr), "n_test": len(dte), "n_races_test": nr,
               "coef": dict(zip(FEATURES, w.tolist()))}
    (PROC / "metrics.json").write_text(json.dumps(metrics, indent=2))
    cal.to_csv(TABLES / "calibration.csv", index=False)
    return dall


if __name__ == "__main__":
    run()
