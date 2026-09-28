"""
collect_data.py — Kumpulkan data balap massal (zero-browser).

Alur:
  1. discover_races() -> daftar URL race
  2. scrape_race() per URL -> event + selections
  3. simpan ke data/raw/ (JSON per race) + CSV gabungan

Jalankan:
    python src/collect_data.py discover          # lihat jumlah race
    python src/collect_data.py collect 50        # scrape 50 race
"""

from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from racenet_scraper import scrape_race, discover_races  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
RACES_DIR = RAW / "races"
RACES_DIR.mkdir(exist_ok=True)

# ---- skema CSV kaya (dari selection racenet) ----
COLS = [
    "race_url", "meeting_name", "meeting_date", "track", "track_condition",
    "race_number", "race_name", "distance", "race_class", "prize_money",
    "starters", "is_resulted", "status",
    # selection (per kuda)
    "competitor_number", "barrier", "horse_name", "horse_age", "horse_sex",
    "horse_colour", "sire", "dam", "status_sel", "weight", "jockey_weight",
    "jockey", "trainer",
    # performa
    "career", "win_pct", "place_pct", "roi", "last_run_finish_pos",
    "last_run_sp", "trainer_jockey_win", "days_since_last_run",
    "avgL200", "avgL400", "avgL600", "avgL800", "avgRT",
    "form_letters",
    # odds
    "best_win_odds", "avg_win_odds", "n_bookmakers", "n_flucs",
    "fluc_open", "fluc_last", "fluc_move_pct",
    # hasil (target)
    "finish_position", "result_position", "won",
]


def extract_rows(event: dict, url: str) -> list[dict]:
    """Ubah 1 event -> baris per kuda (siap CSV)."""
    meeting = event.get("_meeting") or {}
    venue = (meeting.get("venue") or {}) if meeting else {}
    rows = []
    for sel in (event.get("selections") or []):
        comp = sel.get("competitor") or {}
        stats = sel.get("stats") or {}
        jock = sel.get("jockey") or {}
        trainer = sel.get("trainer") or {}
        bm = sel.get("bookmakerWinOdds") or []
        flucs = sel.get("flucOdds") or []
        best = sel.get("bestWinOdds") or []

        # odds: best & average
        def od(item):
            try:
                return float(item.get("price", {}).get("value"))
            except Exception:
                return None
        best_od = od(best[0]) if best else None
        avg_raw = sel.get("averageWinOdds") or {}
        if isinstance(avg_raw, dict) and "price" in avg_raw:
            avg_od = od(avg_raw)
        elif isinstance(avg_raw, (int, float)):
            avg_od = float(avg_raw) if avg_raw else None
        else:
            avg_od = od(avg_raw)

        # fluc open/last
        f_vals = [f.get("value") for f in flucs if f.get("value") is not None]
        f_open = f_vals[0] if f_vals else None
        f_last = f_vals[-1] if f_vals else None
        f_move = None
        if f_open and f_last and f_open > 0:
            f_move = round((f_last - f_open) / f_open * 100, 1)

        # hasil (jika sudah ada) — racenet menaruh di result.finishPosition
        res = sel.get("result") or {}
        fin_pos = None
        if isinstance(res, dict):
            fin_pos = res.get("finishPosition")
        sr = sel.get("selectionResult") or {}
        res_pos = sr.get("finishPosition") if isinstance(sr, dict) else None
        try:
            fin_pos = int(fin_pos) if fin_pos is not None else None
        except (TypeError, ValueError):
            fin_pos = None
        if fin_pos is None:
            try:
                fin_pos = int(res_pos) if res_pos is not None else None
            except (TypeError, ValueError):
                fin_pos = None
        final_pos = fin_pos

        rows.append({
            "race_url": url,
            "meeting_name": meeting.get("name") or venue.get("name"),
            "meeting_date": meeting.get("meetingDateLocal"),
            "track": venue.get("name"),
            "track_condition": event.get("trackCondition"),
            "race_number": event.get("eventNumber"),
            "race_name": event.get("name"),
            "distance": event.get("distance"),
            "race_class": event.get("eventClass"),
            "prize_money": event.get("racePrizeMoney"),
            "starters": event.get("starters"),
            "is_resulted": event.get("isResulted"),
            "status": sel.get("status"),
            "competitor_number": sel.get("competitorNumber"),
            "barrier": sel.get("barrierNumber"),
            "horse_name": comp.get("name"),
            "horse_age": comp.get("age"),
            "horse_sex": comp.get("sex"),
            "horse_colour": comp.get("colour"),
            "sire": comp.get("sire"),
            "dam": comp.get("dam"),
            "status_sel": sel.get("status"),
            "weight": sel.get("weight"),
            "jockey_weight": sel.get("jockeyWeight"),
            "jockey": jock.get("name"),
            "trainer": trainer.get("name"),
            "career": stats.get("career"),
            "win_pct": stats.get("winPercentage"),
            "place_pct": stats.get("placePercentage"),
            "roi": stats.get("roi"),
            "last_run_finish_pos": stats.get("lastRunFinishPosition"),
            "last_run_sp": stats.get("lastRunStartingPrice"),
            "trainer_jockey_win": stats.get("trainerJockeyWin"),
            "days_since_last_run": stats.get("daysSinceLastRun"),
            "avgL200": stats.get("avgL200"),
            "avgL400": stats.get("avgL400"),
            "avgL600": stats.get("avgL600"),
            "avgL800": stats.get("avgL800"),
            "avgRT": stats.get("avgRT"),
            "form_letters": sel.get("formLetters"),
            "best_win_odds": best_od,
            "avg_win_odds": avg_od,
            "n_bookmakers": len(bm),
            "n_flucs": len(flucs),
            "fluc_open": f_open,
            "fluc_last": f_last,
            "fluc_move_pct": f_move,
            "finish_position": final_pos,
            "result_position": sel.get("resultPosition"),
            "won": (1 if final_pos == 1 else (0 if final_pos else None)),
        })
    return rows


def collect(n_races: int, date_filter: str | None = None):
    races = discover_races(date_filter)
    print(f"discovered {len(races)} races")
    if n_races:
        races = races[:n_races]

    all_rows = []
    ok = 0
    for i, url in enumerate(races, 1):
        # cari meeting context untuk track name
        ev = scrape_race(url)
        if not ev:
            print(f"  [{i}/{len(races)}] FAIL {url[-60:]}")
            continue
        rows = extract_rows(ev, url)
        all_rows.extend(rows)
        ok += 1
        # simpan JSON mentah per race
        slug = url.rstrip("/").split("/")[-2][:80]
        (RACES_DIR / f"{slug}.json").write_text(
            json.dumps(ev, ensure_ascii=False), encoding="utf-8")
        print(f"  [{i}/{len(races)}] OK {len(rows)} horses  {slug[:45]}")
        # simpan CSV progresif
        if all_rows:
            with open(RAW / "races_raw.csv", "w", newline="", encoding="utf-8-sig") as f:
                w = csv.DictWriter(f, fieldnames=COLS)
                w.writeheader()
                w.writerows(all_rows)

    print(f"\nDONE: {ok}/{len(races)} races, {len(all_rows)} horse-rows")
    return all_rows


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "collect"
    if mode == "discover":
        races = discover_races(sys.argv[2] if len(sys.argv) > 2 else None)
        print(f"total races: {len(races)}")
    else:
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        collect(n)
