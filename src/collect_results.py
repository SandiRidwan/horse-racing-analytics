"""
collect_results.py — Kumpulkan data RACE HASIL (untuk training ML).

TEMUAN PENTING (reverse engineering):
  /results/horse-racing/{track}/{YYYY-MM-DD}  -> memuat SELURUH meeting hari itu
  (bukan hanya track di URL). Struktur: meetings[] -> events[] -> selections[]
  Setiap meeting punya: name, venue{name,state}, country, meetingDateLocal.
  Setiap selection punya selection.result.finishPosition (TARGET ML).

Jadi cukup 1 request per TANGGAL -> ratusan race sekaligus (efisien).

Output: data/raw/races_raw.csv (dengan kolom finish_position + won)
"""

from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import racenet_scraper as R  # noqa: E402
from collect_data import extract_rows, COLS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
BASE = R.BASE


def fetch_with_retry(url, tries=15):
    for _ in range(tries):
        h = R.fetch_html(url, tries=1)
        if h:
            return h
    return None


def find_meetings(data) -> list[dict]:
    """Kumpulkan semua node bertipe Meeting (punya events[] + venue)."""
    acc = []

    def walk(o, depth=0):
        if depth > 9:
            return
        if isinstance(o, dict):
            if "events" in o and isinstance(o["events"], list) and "venue" in o:
                acc.append(o)
            for v in o.values():
                walk(v, depth + 1)
        elif isinstance(o, list):
            for v in o:
                walk(v, depth + 1)
    walk(data)
    # dedup by id
    seen, uniq = set(), []
    for m in acc:
        if m.get("id") not in seen:
            seen.add(m.get("id"))
            uniq.append(m)
    return uniq


def scrape_date(date_str: str) -> list[dict]:
    """Ambil SEMUA race (hasil) untuk satu tanggal."""
    url = f"{BASE}/results/horse-racing/caulfield/{date_str}"
    html = fetch_with_retry(url)
    if not html:
        return []
    data = R.decode_nuxt(html)
    if not data:
        return []

    meetings = find_meetings(data)
    rows = []
    for meet in meetings:
        venue = meet.get("venue") or {}
        ctry = venue.get("country") or {}
        ctx = {
            "name": meet.get("name"),
            "meetingDateLocal": meet.get("meetingDateLocal"),
            "venue": venue,
            "country": ctry.get("iso3") or ctry.get("name"),
            "state": venue.get("state"),
            "railPosition": meet.get("railPosition"),
        }
        for ev in (meet.get("events") or []):
            if not isinstance(ev, dict) or not ev.get("selections"):
                continue
            ev["_meeting"] = ctx
            rows.extend(extract_rows(ev, url))
    return rows


def collect(dates: list[str]):
    all_rows = []
    for date_str in dates:
        rows = scrape_date(date_str)
        all_rows.extend(rows)
        got = sum(1 for r in rows if r.get("finish_position"))
        print(f"  {date_str}: {len(rows)} horses ({got} hasil) "
              f"[{len(set(r['race_url']+str(r['race_number']) for r in rows))} races]")
        if all_rows:
            with open(RAW / "races_raw.csv", "w", newline="", encoding="utf-8-sig") as f:
                w = csv.DictWriter(f, fieldnames=COLS)
                w.writeheader()
                w.writerows(all_rows)

    with_res = sum(1 for r in all_rows if r.get("finish_position"))
    print(f"\nDONE: {len(all_rows)} rows; {with_res} dengan hasil "
          f"({with_res*100//max(1,len(all_rows))}%)")
    return all_rows


if __name__ == "__main__":
    # tanggal: dari argumen (bisa beberapa) atau default
    dates = sys.argv[1:] if len(sys.argv) > 1 else ["2026-09-27"]
    collect(dates)
