"""
insight.py — kotak 'Insight & Rekomendasi' untuk bawah setiap chart.

Setiap chart harus menjawab tiga hal (pola wajib portofolio):
  · KESIMPULAN   — "dari chart ini kita bisa simpulkan ..."
  · REKOMENDASI  — tindakan konkret seolah kita PEMILIK data (agar hasil ideal)
  · RISIKO       — apa yang terjadi bila diabaikan / salah tafsir

Fungsi `box()` merender kotak menonjol di Streamlit; `text()` untuk README.
Konten disimpan sebagai data (dict) agar dapat diaudit & diuji kelengkapannya.
"""

from __future__ import annotations

INSIGHTS: dict[str, dict] = {}


def register(key: str, kesimpulan: str, rekomendasi: list[str],
             risiko: str, tingkat: str = "sedang") -> None:
    """Daftarkan insight untuk sebuah key chart."""
    INSIGHTS[key] = {
        "kesimpulan": kesimpulan,
        "rekomendasi": rekomendasi,
        "risiko": risiko,
        "tingkat": tingkat,   # 'kritis' | 'tinggi' | 'sedang' | 'rendah'
    }


_TONE = {
    "kritis": ("#7f1d1d", "#fca5a5", "🔴 KRITIS"),
    "tinggi": ("#78350f", "#fcd34d", "🟠 PERHATIAN"),
    "sedang": ("#1e3a5f", "#93c5fd", "🔵 INSIGHT"),
    "rendah": ("#14532d", "#86efac", "🟢 SEHAT"),
}


def box(key: str, st=None) -> None:
    """Render kotak 'Insight & Rekomendasi' di Streamlit."""
    if st is None:
        import streamlit as st  # noqa
    ins = INSIGHTS.get(key)
    if not ins:
        return
    bg, fg, badge = _TONE.get(ins.get("tingkat", "sedang"), _TONE["sedang"])
    recs = "".join(f"<li>{r}</li>" for r in ins["rekomendasi"])
    st.markdown(
        f"""
        <div style="background:{bg};border-left:5px solid {fg};
        padding:16px 20px;border-radius:10px;margin:6px 0 18px 0;">
          <div style="color:{fg};font-weight:800;font-size:.82rem;
          letter-spacing:.08em;margin-bottom:8px;">{badge} · INSIGHT &amp;
          REKOMENDASI</div>
          <div style="color:#E8EEF4;font-size:.92rem;margin-bottom:10px;">
          <b>Kesimpulan.</b> {ins['kesimpulan']}</div>
          <div style="color:#CBD5E1;font-size:.88rem;">
          <b>Rekomendasi tindakan:</b>
          <ul style="margin:6px 0 10px 18px;">{recs}</ul></div>
          <div style="color:#f0b8b8;font-size:.84rem;border-top:1px solid
          rgba(255,255,255,.12);padding-top:8px;">
          <b>⚠️ Risiko bila diabaikan.</b> {ins['risiko']}</div>
        </div>""", unsafe_allow_html=True)


def text(key: str) -> str:
    """Render sebagai markdown untuk README."""
    ins = INSIGHTS.get(key)
    if not ins:
        return ""
    recs = "\n".join(f"  - {r}" for r in ins["rekomendasi"])
    return (f"**Kesimpulan.** {ins['kesimpulan']}\n\n"
            f"**Rekomendasi tindakan:**\n{recs}\n\n"
            f"**⚠️ Risiko bila diabaikan.** {ins['risiko']}")


def audit(required_keys: list[str] | None = None, verbose: bool = True) -> bool:
    """Pastikan setiap insight lengkap (kesimpulan, >=1 rekomendasi, risiko)."""
    ok = True
    for k, v in INSIGHTS.items():
        miss = []
        if not v.get("kesimpulan"):
            miss.append("kesimpulan")
        if not v.get("rekomendasi"):
            miss.append("rekomendasi")
        if not v.get("risiko"):
            miss.append("risiko")
        if miss:
            ok = False
            if verbose:
                print(f"  MISSING {k}: {miss}")
    if required_keys:
        for k in required_keys:
            if k not in INSIGHTS:
                ok = False
                if verbose:
                    print(f"  MISSING key: {k}")
    if verbose:
        print(f"Insight: {len(INSIGHTS)} | "
              f"{'SEMUA LENGKAP' if ok else 'ADA YANG KURANG'}")
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if audit() else 1)
