"""
render_readme_insights.py — hasilkan seksi 'Insight & Rekomendasi' untuk README
dari src/insights_content.py, lalu sisipkan ke README.md.

Idempoten: mengganti blok antara penanda
  <!-- INSIGHTS:START --> ... <!-- INSIGHTS:END -->
bila sudah ada, atau menambahkan sebelum bagian terakhir bila belum.

Jalankan dari root project: python scripts/render_readme_insights.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import insight as INS  # noqa: E402
import insights_content  # noqa: E402,F401

START = "<!-- INSIGHTS:START -->"
END = "<!-- INSIGHTS:END -->"

ORDER_HINT = None  # urut sesuai deklarasi di insights_content

# Judul manusiawi untuk key yang tidak enak dibaca otomatis.
TITLE_MAP = {
    "kpi": "KPI / Ringkasan",
    "result_table": "Hasil Uji Statistik",
    "ci_plot": "Efek & Confidence Interval",
    "rank_evolution": "Evolusi Peringkat",
}


def _title(key: str) -> str:
    if key in TITLE_MAP:
        return TITLE_MAP[key]
    return " ".join(w.upper() if len(w) <= 3 and w.isalpha() else w.title()
                    for w in key.replace("_", " ").split())


def build_block() -> str:
    lines = [START,
             "## 💡 Insight & Rekomendasi (per analisis)",
             "",
             "_Setiap analisis disertai kesimpulan, rekomendasi tindakan, dan "
             "risiko bila diabaikan — bukan sekadar angka._",
             ""]
    badge = {"kritis": "🔴", "tinggi": "🟠", "sedang": "🔵", "rendah": "🟢"}
    # urutkan: kritis → tinggi → sedang → rendah
    rank = {"kritis": 0, "tinggi": 1, "sedang": 2, "rendah": 3}
    items = sorted(INS.INSIGHTS.items(),
                   key=lambda kv: rank.get(kv[1].get("tingkat", "sedang"), 9))
    for key, v in items:
        icon = badge.get(v.get("tingkat", "sedang"), "🔵")
        title = _title(key)
        lines.append(f"### {icon} {title}")
        lines.append(f"**Kesimpulan.** {v['kesimpulan']}")
        lines.append("")
        lines.append("**Rekomendasi tindakan:**")
        for r in v["rekomendasi"]:
            lines.append(f"- {r}")
        lines.append("")
        lines.append(f"**⚠️ Risiko bila diabaikan.** {v['risiko']}")
        lines.append("")
    lines.append(END)
    return "\n".join(lines)


def main() -> None:
    readme = ROOT / "README.md"
    if not readme.exists():
        raise SystemExit("README.md tidak ditemukan")
    text = readme.read_text(encoding="utf-8")
    block = build_block()

    if START in text and END in text:
        text = re.sub(re.escape(START) + r".*?" + re.escape(END), block,
                      text, flags=re.DOTALL)
        print(f"[readme] blok insight diganti ({len(INS.INSIGHTS)} item)")
    else:
        # sisipkan sebelum bagian 'Author' bila ada, jika tidak di akhir
        m = re.search(r"\n##\s+👤", text)
        if m:
            text = text[:m.start()] + "\n" + block + "\n" + text[m.start():]
        else:
            text = text.rstrip() + "\n\n" + block + "\n"
        print(f"[readme] blok insight ditambahkan ({len(INS.INSIGHTS)} item)")

    readme.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
