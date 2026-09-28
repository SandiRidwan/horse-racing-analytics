"""
features_v2.py — FEATURE ENGINEERING MENDALAM dari JSON racenet.

Menggali SEMUA sinyal yang tersedia (jauh lebih kaya dari features_raw):
  A. Riwayat bentuk (forms[]) — 5 start terakhir per kuda
       - rata-rata/maks posisi finis, rasio menang/placed, margin rata-rata,
         SP rata-rata, jumlah hari sejak lari, tren bentuk (recent vs older),
         handicap rating terakhir, jumlah start di track/jarak/kelas sama
  B. Statistik karier (stats) — win%, place%, ROI, prize, rating,
       strike-rate per kondisi (turf/synthetic/firm/good/soft/heavy/wet/dry),
       firstUp/secondUp/thirdUp, favourite rate, dsb.
  C. Koneksi — jockey & trainer agregat (dibangun lintas-dataset),
       trainerJockeyWin, jockeyHorse record
  D. Market — best_win_odds, implied prob, fluc open/last/move, jumlah bookmaker,
       konsensus pasar (rata-rata odds), overround per race
  E. Konteks race — jarak, starters, hadiah, kelas, tipe track, kondisi
  F. Punters Edge rating, star ratings, weight, jockey claim

Output: data/processed/features_v2.csv
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RACES = ROOT / "data" / "raw" / "races"
PROC = ROOT / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)


def _f(x):
    try:
        if x is None or x == "":
            return np.nan
        return float(str(x).replace(",", ""))
    except (ValueError, TypeError):
        return np.nan


def _record(s):
    """'6:3-1-1' -> (runs, wins, sec, third, win_rate, place_rate)."""
    if not isinstance(s, str):
        return (np.nan,) * 6
    m = re.match(r"(\d+):(\d+)-(\d+)-(\d+)", s.strip())
    if not m:
        return (np.nan,) * 6
    r, w, s2, t = (int(g) for g in m.groups())
    return (r, w, s2, t,
            (w / r if r else np.nan),
            ((w + s2 + t) / r if r else np.nan))


def parse_forms(forms: list) -> dict:
    """Agregasi 5 start terakhir -> fitur bentuk."""
    if not forms:
        return {}
    pos, margins, sps, days, hr = [], [], [], [], []
    n_track = n_dist = n_class = n_fav = n_firstup = 0
    for f in forms:
        fp = _f(f.get("finishPosition"))
        if not np.isnan(fp) and fp > 0:
            pos.append(fp)
        m = _f(f.get("margin"))
        if not np.isnan(m):
            margins.append(m)
        sp = _f(f.get("startingWinPriceDecimal"))
        if not np.isnan(sp):
            sps.append(sp)
        d = _f(f.get("daysSinceLastRun"))
        if not np.isnan(d):
            days.append(d)
        h = _f(f.get("handicapRating"))
        if not np.isnan(h):
            hr.append(h)
        n_track += bool(f.get("isTrack"))
        n_dist += bool(f.get("isDistance"))
        n_class += bool(f.get("isClass"))
        n_fav += bool(f.get("isFavourite"))
        n_firstup += bool(f.get("isFirstUp"))
    n = len(forms)
    out = {
        "form_n": n,
        "form_pos_mean": np.mean(pos) if pos else np.nan,
        "form_pos_best": np.min(pos) if pos else np.nan,
        "form_pos_worst": np.max(pos) if pos else np.nan,
        "form_win_rate": sum(1 for p in pos if p == 1) / n if n else np.nan,
        "form_place_rate": sum(1 for p in pos if p <= 3) / n if n else np.nan,
        "form_top2_rate": sum(1 for p in pos if p <= 2) / n if n else np.nan,
        "form_margin_mean": np.mean(margins) if margins else np.nan,
        "form_sp_mean": np.mean(sps) if sps else np.nan,
        "form_days_mean": np.mean(days) if days else np.nan,
        "form_hr_mean": np.mean(hr) if hr else np.nan,
        "form_hr_last": hr[0] if hr else np.nan,
        "form_n_track": n_track, "form_n_dist": n_dist,
        "form_n_class": n_class, "form_n_fav": n_fav,
        "form_n_firstup": n_firstup,
    }
    # tren bentuk: 2 start terbaru vs 3 sebelumnya (posisi lebih kecil = lebih baik)
    if len(pos) >= 3:
        recent = np.mean(pos[:2])
        older = np.mean(pos[2:])
        out["form_trend"] = older - recent  # positif = makin baik
    else:
        out["form_trend"] = np.nan
    return out


def parse_stats(st: dict) -> dict:
    """Agregasi stats karier -> fitur."""
    if not st:
        return {}
    out = {
        "win_pct": _f(st.get("winPercentage")),
        "place_pct": _f(st.get("placePercentage")),
        "roi": _f(st.get("roi")),
        "rating": _f(st.get("rating")),
        "total_prize": _f(st.get("totalPrizeMoney")),
        "avg_prize": _f(st.get("averagePrizeMoney")),
        "tj_win": _f(st.get("trainerJockeyWin")),
        "days_since_run": _f(st.get("daysSinceLastRun")),
        "last_run_finish": _f(st.get("lastRunFinishPosition")),
        "last_run_sp": _f(st.get("lastRunStartingPrice")),
        "avgRT": _f(st.get("avgRT")),
        "avgL200": _f(st.get("avgL200")),
        "avgL400": _f(st.get("avgL400")),
        "avgL600": _f(st.get("avgL600")),
        "avgL800": _f(st.get("avgL800")),
    }
    # record string -> rates
    for key, col in [("career", "career"), ("lastYear", "ly"),
                     ("currentSeason", "cs"), ("distance", "dist"),
                     ("track", "trk"), ("trackDistance", "trkdist"),
                     ("turf", "turf"), ("synthetic", "synth"),
                     ("firstUp", "firstup"), ("secondUp", "secondup"),
                     ("thirdUp", "thirdup"), ("firm", "firm"),
                     ("good", "good"), ("soft", "soft"), ("heavy", "heavy"),
                     ("wet", "wet"), ("dry", "dry"), ("fav", "fav"),
                     ("clockwise", "cw"), ("antiClockwise", "acw"),
                     ("class", "cls")]:
        r = _record(st.get(key))
        out[f"{col}_runs"] = r[0]
        out[f"{col}_winrate"] = r[4]
        out[f"{col}_placerate"] = r[5]
    return out


def build():
    files = sorted(RACES.glob("*.json"))
    print(f"files: {len(files)}")
    rows = []
    for fp in files:
        try:
            ev = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(ev, dict) or "selections" not in ev:
            continue
        meet = ev.get("_meeting") or {}
        venue = meet.get("venue") or {}
        for sel in ev["selections"]:
            comp = sel.get("competitor") or {}
            st = sel.get("stats") or {}
            forms = sel.get("forms") or []
            fl = sel.get("flucOdds") or []
            fvals = [_f(x.get("value")) for x in fl
                     if isinstance(x, dict) and x.get("value") is not None]
            best = sel.get("bestWinOdds") or []
            best_od = np.nan
            if best and isinstance(best[0], dict):
                best_od = _f((best[0].get("price") or {}).get("value"))
            bm = sel.get("bookmakerWinOdds") or []
            bm_vals = [_f((b.get("price") or {}).get("value")) for b in bm
                       if isinstance(b, dict)]
            bm_vals = [v for v in bm_vals if not np.isnan(v) and v > 0]
            res = sel.get("result") or {}
            fin = res.get("finishPosition") if isinstance(res, dict) else None
            try:
                fin = int(fin) if fin not in (None, "", -1) else None
            except (TypeError, ValueError):
                fin = None
            stars = sel.get("starRatings") or []
            star_sum = sum(_f(s.get("rating")) for s in stars
                           if isinstance(s, dict)) if stars else np.nan

            row = {
                "track": venue.get("name") or meet.get("name"),
                "meeting_date": meet.get("meetingDateLocal"),
                "race_number": ev.get("eventNumber"),
                "race_name": ev.get("name"),
                "distance": _f(ev.get("distance")),
                "race_class": ev.get("eventClass"),
                "track_condition": ev.get("trackCondition"),
                "track_type": ev.get("trackType"),
                "group_type": ev.get("groupType"),
                "prize_money": _f(ev.get("racePrizeMoney")),
                "starters": _f(ev.get("starters")),
                "apprentice_claim": bool(ev.get("apprenticeCanClaim")),
                # horse
                "number": _f(sel.get("competitorNumber")),
                "barrier": _f(sel.get("barrierNumber")),
                "weight": _f(sel.get("weight")),
                "jockey_weight": _f(sel.get("jockeyWeight")),
                "jockey_claim": _f(sel.get("jockeyWeightClaim")),
                "rating_official": _f(sel.get("ratingOfficial")),
                "horse": comp.get("name"),
                "age": _f(comp.get("age")),
                "sex": comp.get("sex"),
                "colour": comp.get("colour"),
                "sire": comp.get("sire"),
                "dam": comp.get("dam"),
                "lifetime_stakes": _f(comp.get("lifetimeStakes")),
                "jockey": (sel.get("jockey") or {}).get("name"),
                "trainer": (sel.get("trainer") or {}).get("name"),
                "has_blinkers": bool(sel.get("hasBlinkers")),
                "punters_edge": _f((sel.get("puntersEdge") or {}).get("rating")),
                "star_sum": star_sum,
                "class_change": sel.get("classChange"),
                "form_letters": sel.get("formLetters"),
                # market
                "best_odds": best_od,
                "n_bookmakers": len(bm_vals),
                "bm_mean": float(np.mean(bm_vals)) if bm_vals else np.nan,
                "bm_min": float(np.min(bm_vals)) if bm_vals else np.nan,
                "bm_max": float(np.max(bm_vals)) if bm_vals else np.nan,
                "bm_std": float(np.std(bm_vals)) if len(bm_vals) > 1 else np.nan,
                "n_flucs": len(fvals),
                "fluc_open": fvals[0] if fvals else np.nan,
                "fluc_last": fvals[-1] if fvals else np.nan,
                "fluc_min": float(np.min(fvals)) if fvals else np.nan,
                # target
                "finish_position": fin,
                "won": (1 if fin == 1 else (0 if fin else None)),
            }
            row.update(parse_forms(forms))
            row.update(parse_stats(st))
            rows.append(row)

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["track", "race_number", "number"])
    df.to_csv(PROC / "features_v2.csv", index=False)
    print(f"rows: {len(df)} | cols: {df.shape[1]}")
    print(f"races: {df.groupby(['track','race_number']).ngroups}")
    print(f"dengan hasil: {df['finish_position'].notna().sum()}")
    print(f"dengan odds : {df['best_odds'].notna().sum()}")
    print(f"[OK] -> {PROC/'features_v2.csv'}")
    return df


if __name__ == "__main__":
    build()
