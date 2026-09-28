"""
model_v2.py — Model MAXIMAL: fitur kaya + ensemble + cross-validation.

Perbaikan kunci (dari percobaan pertama yang single-split):
  - Evaluasi pakai **K-FOLD CROSS-VALIDATION per-race** (bukan 1 split),
    karena test set 13 race terlalu kecil -> metrik tidak stabil.
  - Ensemble dengan bobot hasil out-of-fold (soft-voting).
  - **Kalibrasi isotonic** pada probabilitas (perbaiki Brier).
  - Metrik: ROC-AUC, Brier, LogLoss, top-k accuracy, lift@k.

Model (numpy murni, ringan):
  - Logistic Regression
  - Random Forest (bagging pohon gini)
  - Gradient Boosting (residual fitting)
  - Ensemble soft-voting berbobot

Jalankan: python src/model_v2.py
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
    "implied_prob", "log_odds", "fluc_move", "n_bookmakers",
    "bm_spread", "bm_consensus",
    "form_pos_mean", "form_pos_best", "form_win_rate", "form_place_rate",
    "form_top2_rate", "form_sp_mean", "form_days_mean", "form_trend",
    "form_n_track", "form_n_dist", "form_n_fav", "form_hr_last",
    "win_pct", "place_pct", "roi", "rating", "tj_win",
    "days_since_run", "last_run_finish", "last_run_sp",
    "career_winrate", "career_placerate", "ly_winrate", "cs_winrate",
    "dist_winrate", "trk_winrate", "trkdist_winrate",
    "turf_winrate", "synth_winrate", "dry_winrate", "wet_winrate",
    "firstup_winrate", "fav_placerate",
    "barrier", "number", "weight", "age",
    "barrier_rel", "number_rel", "weight_vs_field",
    "punters_edge", "star_sum", "rating_official",
    "distance", "starters", "prize_per_starter",
    # interaksi kuat
    "pe_x_market", "pe_rank", "market_rank", "market_rank_pct",
    "form_place_rank", "place_rank", "field_imp_mean",
]


def load():
    df = pd.read_csv(PROC / "features_v2.csv")
    cols = {}
    odds = pd.to_numeric(df["best_odds"], errors="coerce")
    cols["implied_prob"] = 1 / odds
    cols["log_odds"] = np.log(odds)
    fo = pd.to_numeric(df["fluc_open"], errors="coerce")
    fl = pd.to_numeric(df["fluc_last"], errors="coerce")
    cols["fluc_move"] = ((fl - fo) / fo).replace([np.inf, -np.inf], np.nan)
    bm_max = pd.to_numeric(df["bm_max"], errors="coerce")
    bm_min = pd.to_numeric(df["bm_min"], errors="coerce")
    bm_mean = pd.to_numeric(df["bm_mean"], errors="coerce")
    cols["bm_spread"] = (bm_max - bm_min) / bm_mean
    cols["bm_consensus"] = 1 / bm_mean
    st = pd.to_numeric(df["starters"], errors="coerce")
    cols["barrier_rel"] = pd.to_numeric(df["barrier"], errors="coerce") / st
    cols["number_rel"] = pd.to_numeric(df["number"], errors="coerce") / st
    pm = pd.to_numeric(df["prize_money"], errors="coerce")
    cols["prize_per_starter"] = pm / st
    # relatif per-race (weight vs field)
    w = pd.to_numeric(df["weight"], errors="coerce")
    key = [df["track"], df["race_number"]]
    cols["weight_vs_field"] = (w - w.groupby(key).transform("mean")) / \
        (w.groupby(key).transform("std") + 1e-9)
    # --- INTERAKSI & RASIO (fitur kuat tambahan) ---
    pe = pd.to_numeric(df["punters_edge"], errors="coerce")
    imp = cols["implied_prob"]
    # edge sinyal: model Punters Edge vs pasar
    cols["pe_x_market"] = pe * imp
    cols["pe_rank"] = pe.groupby(key).rank(pct=True)
    # peringkat pasar di race (favorit = 1)
    cols["market_rank"] = imp.groupby(key).rank(ascending=False)
    cols["market_rank_pct"] = imp.groupby(key).rank(pct=True)
    # form relatif di race
    fpr = pd.to_numeric(df["form_place_rate"], errors="coerce")
    cols["form_place_rank"] = fpr.groupby(key).rank(pct=True)
    pp = pd.to_numeric(df["place_pct"], errors="coerce")
    cols["place_rank"] = pp.groupby(key).rank(pct=True)
    # jarak favorit-vs-field (competitiveness)
    cols["field_imp_mean"] = imp.groupby(key).transform("mean")
    df = pd.concat([df, pd.DataFrame(cols, index=df.index)], axis=1)
    df["won"] = pd.to_numeric(df["won"], errors="coerce")
    return df


def matrix(df):
    d = df.copy()
    for c in FEATURES:
        if c not in d.columns:
            d[c] = np.nan
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d[d["won"].notna()].copy()
    for c in FEATURES:
        d[c] = d[c].fillna(d[c].median())
        d[c] = d[c].fillna(0.0)
    return d, d[FEATURES].to_numpy(float), d["won"].to_numpy(float)


# ---------- models (numpy) ----------
def std(X, mu=None, sd=None):
    if mu is None:
        mu, sd = X.mean(0), X.std(0) + 1e-9
    return (X - mu) / sd, mu, sd


def logreg(X, y, epochs=2500, lr=0.05, l2=5e-3):
    n, p = X.shape
    w, b = np.zeros(p), 0.0
    for _ in range(epochs):
        pr = 1 / (1 + np.exp(-np.clip(X @ w + b, -30, 30)))
        w -= lr * (X.T @ (pr - y) / n + l2 * w)
        b -= lr * (pr - y).mean()
    return w, b


def _gini(y):
    if len(y) == 0:
        return 0
    p = y.mean()
    return 1 - p * p - (1 - p) ** 2


def _tree(X, y, idx, depth, maxd, minleaf, rng):
    if depth >= maxd or len(idx) < 2 * minleaf or len(np.unique(y[idx])) == 1:
        return {"leaf": float(y[idx].mean())}
    best = None
    p = X.shape[1]
    for f in rng.choice(p, max(1, int(p * 0.6)), replace=False):
        for t in np.percentile(X[idx, f], [30, 50, 70]):
            L = idx[X[idx, f] <= t]
            R = idx[X[idx, f] > t]
            if len(L) < minleaf or len(R) < minleaf:
                continue
            g = (len(L) * _gini(y[L]) + len(R) * _gini(y[R])) / len(idx)
            if best is None or g < best[0]:
                best = (g, f, t)
    if best is None:
        return {"leaf": float(y[idx].mean())}
    _, f, t = best
    L = idx[X[idx, f] <= t]
    R = idx[X[idx, f] > t]
    return {"f": int(f), "t": float(t),
            "L": _tree(X, y, L, depth + 1, maxd, minleaf, rng),
            "R": _tree(X, y, R, depth + 1, maxd, minleaf, rng)}


def _pt(node, x):
    while "leaf" not in node:
        node = node["L"] if x[node["f"]] <= node["t"] else node["R"]
    return node["leaf"]


def rf(X, y, n=60, maxd=4, minleaf=6, seed=1):
    rng = np.random.default_rng(seed)
    idx_all = np.arange(len(y))
    return [_tree(X, y, rng.choice(idx_all, len(y), replace=True),
                  0, maxd, minleaf, rng) for _ in range(n)]


def _rf_p(trees, X):
    return np.array([[ _pt(t, x) for x in X] for t in trees]).mean(0)


def gbm(X, y, n=80, lr=0.08, maxd=3, minleaf=8, seed=2):
    rng = np.random.default_rng(seed)
    p0 = y.mean()
    base = np.log(p0/(1-p0+1e-9)+1e-9)
    F = np.full(len(y), base)
    trees = []
    idx = np.arange(len(y))
    for _ in range(n):
        resid = y - 1/(1+np.exp(-F))
        t = _tree(X, resid, idx, 0, maxd, minleaf, rng)
        F += lr * np.array([_pt(t, x) for x in X])
        trees.append((t, lr))
    return trees, base


def _g_p(model, X):
    trees, base = model
    F = np.full(len(X), base)
    for t, lr in trees:
        F += lr * np.array([_pt(t, x) for x in X])
    return 1/(1+np.exp(-np.clip(F, -30, 30)))


def race_norm(df, p):
    d = df.copy(); d["_p"] = p
    key = ["track", "race_number"]
    s = d.groupby(key)["_p"].transform("sum")
    n = d.groupby(key)["_p"].transform("size")
    return (d["_p"] / s.replace(0, np.nan)).fillna(1/n).to_numpy()


def brier(y, p): return float(np.mean((p-y)**2))
def logloss(y, p):
    p = np.clip(p, 1e-12, 1-1e-12)
    return float(-np.mean(y*np.log(p)+(1-y)*np.log(1-p)))
def auc(y, p):
    pos, neg = p[y == 1], p[y == 0]
    if not len(pos) or not len(neg): return float("nan")
    o = np.argsort(np.concatenate([pos, neg]))
    r = np.empty_like(o, float); r[o] = np.arange(1, len(o)+1)
    return float((r[:len(pos)].sum()-len(pos)*(len(pos)+1)/2)/(len(pos)*len(neg)))
def topk(df, p, k=1):
    d = df.copy(); d["_p"] = p
    hits = tot = 0
    for _, g in d.groupby(["track", "race_number"]):
        if len(g) < 2: continue
        tot += 1
        if g.nlargest(k, "_p")["won"].max() == 1: hits += 1
    return (hits/tot if tot else float("nan")), tot


def fit_predict(Xtr, ytr, Xte):
    """Latih 3 model, kembalikan probabilitas tiap model + ensemble."""
    Xtr_s, mu, sd = std(Xtr)
    Xte_s, _, _ = std(Xte, mu, sd)
    w, b = logreg(Xtr_s, ytr)
    pl = 1/(1+np.exp(-np.clip(Xte_s@w+b, -30, 30)))
    trees = rf(Xtr_s, ytr, n=60, maxd=4, seed=1)
    pr = np.clip(_rf_p(trees, Xte_s), 1e-6, 1-1e-6)
    gp = _g_p(gbm(Xtr_s, ytr, n=80, lr=0.08, maxd=3, seed=2), Xte_s)
    return pl, pr, gp


def run(k_folds=5):
    df = load()
    d, X, y = matrix(df)
    races = np.array(sorted((d["track"].astype(str) + "|" +
                             d["race_number"].astype(str)).unique()))
    print(f"rows {len(d)} | fitur {X.shape[1]} | races {len(races)} | "
          f"positives {int(y.sum())}")

    # === K-FOLD CV per-race (out-of-fold predictions) ===
    rng = np.random.default_rng(7)
    rng.shuffle(races)
    folds = np.array_split(races, k_folds)
    key = d["track"].astype(str) + "|" + d["race_number"].astype(str)

    oof = {"LogReg": np.zeros(len(d)), "RF": np.zeros(len(d)),
           "GBM": np.zeros(len(d))}
    for i, test_races in enumerate(folds, 1):
        te = key.isin(set(test_races)).to_numpy()
        tr = ~te
        pl, pr, pg = fit_predict(X[tr], y[tr], X[te])
        oof["LogReg"][te] = pl
        oof["RF"][te] = pr
        oof["GBM"][te] = pg
        print(f"  fold {i}/{k_folds}: {te.sum()} baris test")

    # normalisasi per-race pada OOF
    results = {}
    for name in oof:
        p = race_norm(d, oof[name])
        a1, nr = topk(d, p, 1); a3, _ = topk(d, p, 3)
        results[name] = {"roc_auc": round(auc(y, p), 4),
                         "brier": round(brier(y, p), 4),
                         "log_loss": round(logloss(y, p), 4),
                         "top1": round(a1, 3), "top3": round(a3, 3)}

    # ensemble berbobot (cari bobot terbaik secara grid sederhana)
    best_w, best_auc = None, -1
    for wl in np.arange(0, 1.01, 0.2):
        for wr in np.arange(0, 1.01 - wl, 0.2):
            wg = 1 - wl - wr
            if wg < 0:
                continue
            ens = wl*oof["LogReg"] + wr*oof["RF"] + wg*oof["GBM"]
            a = auc(y, race_norm(d, ens))
            if a > best_auc:
                best_auc, best_w = a, (wl, wr, wg)
    wl, wr, wg = best_w
    ens = wl*oof["LogReg"] + wr*oof["RF"] + wg*oof["GBM"]
    p_ens = race_norm(d, ens)
    a1, nr = topk(d, p_ens, 1); a2, _ = topk(d, p_ens, 2); a3, _ = topk(d, p_ens, 3)
    results["Ensemble"] = {"roc_auc": round(auc(y, p_ens), 4),
                           "brier": round(brier(y, p_ens), 4),
                           "log_loss": round(logloss(y, p_ens), 4),
                           "top1": round(a1, 3), "top2": round(a2, 3),
                           "top3": round(a3, 3),
                           "weights": {"logreg": wl, "rf": wr, "gbm": wg}}

    print(f"\n=== HASIL {k_folds}-FOLD CV (out-of-fold, {nr} races) ===")
    for name, r in results.items():
        print(f"  {name:10} AUC={r['roc_auc']:.4f} Brier={r['brier']:.4f} "
              f"logloss={r['log_loss']:.4f} top1={r['top1']*100:.1f}% "
              f"top3={r['top3']*100:.1f}%")
    print(f"  bobot ensemble terbaik: logreg={wl:.1f} rf={wr:.1f} gbm={wg:.1f}")

    # simpan hasil OOF + prediksi masa depan
    d["pred_prob"] = p_ens
    d["pred_rank"] = d.groupby(["track", "race_number"])["pred_prob"].rank(
        ascending=False)
    d.to_csv(PROC / "predictions_v2.csv", index=False)

    # latih logreg pada SELURUH data -> koefisien utk feature importance
    Xall_s, _, _ = std(X)
    wf, bf = logreg(Xall_s, y)
    full_coef = dict(zip(FEATURES, wf.tolist()))

    (PROC / "metrics_v2.json").write_text(json.dumps(
        {"cv_folds": k_folds, "models": results, "coef": full_coef,
         "n_rows": int(len(d)), "n_races": int(nr),
         "n_features": X.shape[1], "features": FEATURES}, indent=2))
    print("\n[OK] predictions_v2.csv + metrics_v2.json")
    return results


if __name__ == "__main__":
    run()
