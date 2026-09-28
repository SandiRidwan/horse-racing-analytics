"""
racenet_scraper.py — ZERO-BROWSER scraper untuk Racenet (Australia).

═══════════════════════════════════════════════════════════════════════════
REVERSE ENGINEERING (temuan lengkap):
═══════════════════════════════════════════════════════════════════════════
1. racenet.com.au = Nuxt (SSR). Data balap di-embed di `window.__NUXT__`
   sebagai fungsi ter-minify:  window.__NUXT__=(function(a,b,...){return {...}}(...))
2. Format itu TIDAK bisa di-parse regex -> dieksekusi via **Node.js** (tersedia).
3. API backend (api.racenet.com.au) di belakang CloudFront signed-URL (403 bila
   dipanggil tanpa signature) -> jadi JANGAN pakai API langsung; pakai HTML SSR.
4. Akses internacional diblokir region + rotasi IP; butuh **proxy residential AU**
   dan RETRY sampai dapat IP bagus (sebagian IP balas 403/202 challenge).
5. Halaman race berisi: event + selections[] (kuda, jockey, trainer, forms,
   odds 19 bookmaker, flucOdds, stats).

METODE: curl_cffi (TLS impersonate) + proxy AU + retry -> HTML SSR ->
        decode window.__NUXT__ via Node -> JSON.
═══════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

from curl_cffi import requests as cffi

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
TMP = ROOT / ".tmp"
TMP.mkdir(exist_ok=True)

BASE = "https://www.racenet.com.au"

# Proxy residential AU (DataImpulse) — kredensial dari traveloka_public/proxy_config.json
PROXY = "http://a635a72792834ec2e48d__cr.au:876be0adb006b4c6@gw.dataimpulse.com:823"

HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "accept-language": "en-AU,en;q=0.9",
    "user-agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
}

MIN_HTML = 500_000     # halaman valid > 500 KB (yg 403 hanya ~1 KB)


def _new_session():
    return cffi.Session(impersonate="chrome124", headers=HEADERS,
                        proxies={"http": PROXY, "https": PROXY})


def fetch_html(url: str, tries: int = 15) -> str | None:
    """Retry sampai dapat IP proxy bagus (200 + HTML besar)."""
    for i in range(tries):
        try:
            s = _new_session()
            r = s.get(url, timeout=45)
            if r.status_code == 200 and len(r.text) >= MIN_HTML:
                return r.text
        except Exception:
            pass
        time.sleep(1.2)
    return None


def decode_nuxt(html: str) -> dict | None:
    """Ekstrak window.__NUXT__ dan jalankan via Node untuk dapat JSON."""
    i = html.find("window.__NUXT__=")
    if i < 0:
        return None
    start = i + len("window.__NUXT__=")
    end = html.find("</script>", start)
    raw = html[start:end].rstrip().rstrip(";")
    if not raw:
        return None
    js_file = TMP / "nuxt_run.js"
    js_file.write_text(
        "try{const x=" + raw +
        ";process.stdout.write(JSON.stringify(x));}catch(e){process.exit(2)}",
        encoding="utf-8")
    try:
        out = subprocess.run(["node", str(js_file)], capture_output=True,
                             text=True, timeout=90, encoding="utf-8")
        if out.returncode == 0 and out.stdout:
            return json.loads(out.stdout)
    except Exception:
        return None
    return None


def scrape_race(url: str) -> dict | None:
    """Scrape satu halaman race -> dict event lengkap + _meeting context.

    Data terbaik ada di data[0].event (punya stats/odds lengkap) dan
    data[0].meeting (context). Keduanya digabung.
    """
    html = fetch_html(url)
    if not html:
        return None
    data = decode_nuxt(html)
    if not data:
        return None

    # struktur racenet: data[0] = { event, meeting, ... }
    node = None
    d0 = data.get("data")
    if isinstance(d0, list) and d0 and isinstance(d0[0], dict):
        node = d0[0]
    if node is None:
        # fallback: cari node dgn event
        def find(o, depth=0):
            if depth > 6:
                return None
            if isinstance(o, dict) and "event" in o:
                return o
            if isinstance(o, dict):
                for v in o.values():
                    r = find(v, depth + 1)
                    if r:
                        return r
            elif isinstance(o, list):
                for v in o:
                    r = find(v, depth + 1)
                    if r:
                        return r
            return None
        node = find(data)
    if not node or "event" not in node:
        return None

    ev = dict(node["event"])
    ev["_meeting"] = node.get("meeting") or {}
    ev["_source_url"] = url
    # pastikan selections lengkap
    if not ev.get("selections"):
        return None
    return ev


def discover_races(date: str | None = None) -> list[str]:
    """Temukan URL race dari halaman form-guide (411+ race/hari).

    Struktur: /form-guide/horse-racing/{track}-{YYYYMMDD}/{race-slug}/overview

    Catatan: versi awal scan salah (slug race bisa punya angka/deskripsi panjang),
    jadi pola link dibuat lebih longgar.
    """
    url = f"{BASE}/form-guide/horse-racing"
    html = fetch_html(url)
    if not html:
        return []
    links = set(re.findall(
        r'href="(/form-guide/horse-racing/[^"/]+/[^"/]+/overview)"', html))
    # buang halaman "all-races" (event ringkas tanpa stats/odds lengkap)
    links = {l for l in links if "/all-races/" not in l}
    races = sorted(BASE + l for l in links)
    if date:
        tag = date.replace("-", "")
        races = [r for r in races if tag in r]
    return races


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "test"
    if mode == "test":
        u = ("https://www.racenet.com.au/form-guide/horse-racing/kilmore-20260928/"
             "bet365-bet-boost-3yo-maiden-plate-race-1/overview")
        ev = scrape_race(u)
        print("event:", ev.get("name") if ev else "FAILED")
        if ev:
            print("selections:", len(ev.get("selections") or []))
    elif mode == "discover":
        date = sys.argv[2] if len(sys.argv) > 2 else "2026-09-28"
        races = discover_races(date)
        print(f"found {len(races)} races on {date}")
        for r in races[:10]:
            print("  ", r)
