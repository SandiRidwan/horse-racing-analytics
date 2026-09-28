"""
build_dataset.py — Bangun dataset ML dari data hasil racenet.

Sumber: data/raw/races_raw.csv (hasil scrape result pages)
Target: `won` (1 = menang, 0 = kalah)

Langkah:
  1. Bersihkan & dedup (track+race_number+race_name+competitor_number)
  2. Feature engineering dari yang tersedia:
     - race-level: starters, distance, prize_money (dibagi starters)
     - horse-level: number, barrier, (status)
     - derived: barrier relatif, posisi nomor
  3. Simpan dataset bersih ke data/processed/

Catatan jujur: racenet results TIDAK menyertakan odds/fit_score, jadi model
memakai fitur struktural (barrier, nomor, field size, hadiah, jarak). Model
odds-based butuh capture real-time pra-race (pipeline 2 fase).
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "races_raw.csv"
PROC = ROOT / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)


def num(x):
    try:
        return float(str(x).replace(",", "").strip())
    except (ValueError, TypeError):
        return np.nan


def parse_career(s: str):
    """'6:0-3-1' -> (starts, wins, seconds, thirds)."""
    if not isinstance(s, str):
        return (np.nan,) * 4
    m = re.match(r"(\d+):(\d+)-(\d+)-(\d+)", s.strip())
    if not m:
        return (np.nan,) * 4
    return tuple(int(g) for g in m.groups())


def main():
    df = pd.read_csv(RAW, dtype=str, low_memory=False)
    print(f"raw: {len(df)} rows")

    # --- nomor & posisi ---
    df["race_number"] = pd.to_numeric(df["race_number"], errors="coerce")
    df["competitor_number"] = pd.to_numeric(df["competitor_number"], errors="coerce")
    df["barrier"] = pd.to_numeric(df["barrier"], errors="coerce")
    df["finish_position"] = pd.to_numeric(df["finish_position"], errors="coerce")
    df["starters"] = pd.to_numeric(df["starters"], errors="coerce")
    df["distance"] = pd.to_numeric(df["distance"], errors="coerce")
    df["prize_money"] = pd.to_numeric(df["prize_money"], errors="coerce")

    # --- dedup: race + nomor kuda ---
    before = len(df)
    df = df.drop_duplicates(subset=["track", "meeting_date", "race_number",
                                    "race_name", "competitor_number"])
    print(f"dedup: {before} -> {len(df)}")

    # --- hasil valid ---
    df = df[(df["finish_position"].notna()) & (df["finish_position"] > 0)].copy()
    print(f"dengan hasil valid: {len(df)}")

    # --- target ---
    df["won"] = (df["finish_position"] == 1).astype(int)
    df["placed"] = (df["finish_position"] <= 3).astype(int)

    # --- feature engineering ---
    # posisi relatif di lapangan (0=sisi dalam, 1=luar)
    df["barrier_rel"] = df["barrier"] / df["starters"]
    df["number_rel"] = df["competitor_number"] / df["starters"]
    # barrier vs nomor (beda)
    df["barrier_minus_no"] = df["barrier"] - df["competitor_number"]
    # hadiah per starter (proxy kualitas race)
    df["prize_per_starter"] = df["prize_money"] / df["starters"]
    # log jarak
    df["log_distance"] = np.log1p(df["distance"])

    # --- negara dari nama track (heuristik) ---
    us_hint = df["track"].str.contains(
        "Downs|Park|Americas|Remon|Star|Worth|Mountain|Fairmount|Woodbine|"
        "Gulfstream|Santa Anita|Los Alamitos|Laurel|Charles Town|Lone Star",
        case=False, na=False)
    df["country_guess"] = np.where(us_hint, "USA", "OTHER")

    keep = ["track", "meeting_name", "meeting_date", "country_guess",
            "race_number", "race_name", "distance", "starters", "prize_money",
            "competitor_number", "barrier", "horse_name",
            "finish_position", "won", "placed",
            "barrier_rel", "number_rel", "barrier_minus_no",
            "prize_per_starter", "log_distance"]

    out = df[keep].copy()
    out.to_csv(PROC / "races_dataset.csv", index=False)

    # ringkas per race
    races = out.groupby(["track", "meeting_date", "race_number"]).size()
    print(f"\ndataset: {len(out)} rows | {len(races)} races | "
          f"avg field {races.mean():.1f}")
    print(f"won rate: {out['won'].mean()*100:.1f}%  (baseline acak = "
          f"{100/races.mean():.1f}%)")
    print(f"tracks: {out['track'].nunique()}")
    print(f"\n[OK] -> {PROC/'races_dataset.csv'}")
    return out


if __name__ == "__main__":
    main()
