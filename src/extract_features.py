"""
extract_features.py — Ekstraksi fitur LENGKAP dari JSON race racenet.

JSON per-race (data/raw/races/*.json) menyimpan event LENGKAP sebelum
dipetakan ke CSV. Di sini kita ambil SEMUA fitur berguna:
  identitas  : horse_name, age, sex, sire, dam, colour
  posisi     : competitor_number, barrier, weight, jockey_weight
  stats      : career, win_pct, place_pct, roi, trainer_jockey_win,
               days_since_last_run, avgL200..avgL800, form_letters
  orang      : jockey, trainer
  odds       : best_win_odds, fluc_open/last (BILA tersedia pra-race)
  konteks    : track, distance, starters, class, prize_money

Ini yang dipakai model ML.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RACES = ROOT / "data" / "raw" / "races"
PROC = ROOT / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)


def _num(x):
    try:
        return float(str(x).replace(",", ""))
    except (ValueError, TypeError):
        return np.nan


def _career(s):
    """'6:0-3-1' -> (runs, wins, seconds, thirds, win_rate)."""
    import re
    if not isinstance(s, str):
        return (np.nan, np.nan, np.nan, np.nan, np.nan)
    m = re.match(r"(\d+):(\d+)-(\d+)-(\d+)", s.strip())
    if not m:
        return (np.nan, np.nan, np.nan, np.nan, np.nan)
    r, w, s2, t = (int(g) for g in m.groups())
    return (r, w, s2, t, (w / r if r else np.nan))


def rows_from_event(ev: dict) -> list[dict]:
    meet = ev.get("_meeting") or {}
    venue = meet.get("venue") or {}
    rows = []
    for sel in (ev.get("selections") or []):
        comp = sel.get("competitor") or {}
        st = sel.get("stats") or {}
        runs, wins, sec, thr, winrate = _career(st.get("career"))
        fl = sel.get("flucOdds") or []
        fvals = [f.get("value") for f in fl if isinstance(f, dict) and f.get("value")]
        best = sel.get("bestWinOdds") or []
        best_od = None
        if best and isinstance(best[0], dict):
            best_od = _num((best[0].get("price") or {}).get("value"))
        res = sel.get("result") or {}
        fin = None
        if isinstance(res, dict):
            fin = res.get("finishPosition")
        try:
            fin = int(fin) if fin not in (None, "", -1) else None
        except (TypeError, ValueError):
            fin = None

        rows.append({
            "track": venue.get("name") or meet.get("name"),
            "meeting_date": meet.get("meetingDateLocal"),
            "race_number": ev.get("eventNumber"),
            "race_name": ev.get("name"),
            "distance": _num(ev.get("distance")),
            "race_class": ev.get("eventClass"),
            "prize_money": _num(ev.get("racePrizeMoney")),
            "starters": _num(ev.get("starters")),
            "is_resulted": ev.get("isResulted"),
            # horse
            "number": _num(sel.get("competitorNumber")),
            "barrier": _num(sel.get("barrierNumber")),
            "weight": _num(sel.get("weight")),
            "jockey_weight": _num(sel.get("jockeyWeight")),
            "horse": comp.get("name"),
            "age": _num(comp.get("age")),
            "sex": comp.get("sex"),
            "sire": comp.get("sire"),
            "dam": comp.get("dam"),
            "jockey": (sel.get("jockey") or {}).get("name"),
            "trainer": (sel.get("trainer") or {}).get("name"),
            # stats
            "career_runs": runs, "career_wins": wins,
            "career_seconds": sec, "career_thirds": thr,
            "career_winrate": winrate,
            "win_pct": _num(st.get("winPercentage")),
            "place_pct": _num(st.get("placePercentage")),
            "roi": _num(st.get("roi")),
            "trainer_jockey_win": _num(st.get("trainerJockeyWin")),
            "days_since_last_run": _num(st.get("daysSinceLastRun")),
            "last_run_finish": _num(st.get("lastRunFinishPosition")),
            "last_run_sp": _num(st.get("lastRunStartingPrice")),
            "avgL200": _num(st.get("avgL200")),
            "avgL400": _num(st.get("avgL400")),
            "avgL600": _num(st.get("avgL600")),
            "avgL800": _num(st.get("avgL800")),
            "avgRT": _num(st.get("avgRT")),
            "form_letters": sel.get("formLetters"),
            "has_blinkers": sel.get("hasBlinkers"),
            # odds
            "best_win_odds": best_od,
            "n_flucs": len(fvals),
            "fluc_open": fvals[0] if fvals else None,
            "fluc_last": fvals[-1] if fvals else None,
            # target
            "finish_position": fin,
            "won": (1 if fin == 1 else (0 if fin else None)),
        })
    return rows


def main():
    files = sorted(RACES.glob("*.json"))
    print(f"JSON race files: {len(files)}")
    all_rows = []
    for fp in files:
        try:
            ev = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(ev, dict) or "selections" not in ev:
            continue
        all_rows.extend(rows_from_event(ev))
    df = pd.DataFrame(all_rows)
    # dedup
    key = ["track", "meeting_date", "race_number", "number"]
    df = df.drop_duplicates(subset=key)
    df.to_csv(PROC / "features_raw.csv", index=False)
    print(f"rows: {len(df)} | races: {df.groupby(['track','race_number']).ngroups}")
    print(f"\nkelengkapan fitur:")
    for c in ["barrier", "jockey", "trainer", "career_runs", "win_pct", "roi",
              "best_win_odds", "fluc_last", "avgL200", "trainer_jockey_win",
              "age", "sex", "finish_position"]:
        if c in df.columns:
            print(f"  {c:20} {df[c].notna().sum()*100//max(1,len(df)):>3}%")
    print(f"\n[OK] -> {PROC/'features_raw.csv'}")
    return df


if __name__ == "__main__":
    main()
