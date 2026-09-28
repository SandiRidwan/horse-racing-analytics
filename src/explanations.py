"""
explanations.py
===============
Narasi penjelasan untuk SETIAP chart & tabel di dashboard Horse Racing.

STANDAR WAJIB (registry E56): setiap elemen visual wajib punya
  · KENAPA   — mengapa analisis ini dipilih
  · TUJUAN   — pertanyaan bisnis yang dijawab
  · DAMPAK   — implikasi / keputusan yang timbul
  plus CARA BACA bila grafik tidak intuitif.
"""

from __future__ import annotations

EXPLAIN = {
    "predictions": {
        "judul": "Prediksi Pemenang per Race",
        "kenapa": "Taruhan/prediksi balap bernilai hanya jika kita bisa "
                  "memperkirakan peluang tiap kuda secara lebih baik daripada "
                  "tebakan pasar (odds). Grafik ini adalah inti model.",
        "tujuan": "Menampilkan probabilitas menang tiap kuda di satu race, "
                  "diurutkan dari yang tertinggi — untuk memilih kandidat.",
        "dampak": "Kuda dengan probabilitas tertinggi menjadi pilihan utama; "
                  "bila probabilitas model > probabilitas tersirat odds, itu "
                  "sinyal 'value bet' (harapan positif).",
        "baca": "Sumbu-X = probabilitas menang (dinormalkan agar total 1 per "
                "race). Sumbu-Y = nama kuda. Batang lebih panjang = lebih diunggulkan.",
    },
    "feature_importance": {
        "judul": "Kepentingan Fitur (Feature Importance)",
        "kenapa": "Model 'black-box' tidak dapat dipercaya. Kita perlu tahu "
                  "faktor apa yang benar-benar menggerakkan prediksi.",
        "tujuan": "Menunjukkan fitur mana yang paling memengaruhi peluang menang "
                  "(mis. odds pasar, bentuk terkini, jockey/trainer).",
        "dampak": "Memvalidasi kewajaran model: bila 'implied_prob' (pasar) "
                  "dominan, model konsisten dengan fakta pasar efisien. Fitur "
                  "tak wajar = tanda model perlu diperiksa.",
        "baca": "Koefisien positif = menaikkan peluang menang; negatif = "
                "menurunkan. Panjang batang = besarnya pengaruh.",
    },
    "calibration": {
        "judul": "Kalibrasi Probabilitas",
        "kenapa": "Probabilitas yang 'bagus' bukan hanya mengurutkan, tapi juga "
                  "harus benar besarannya (mis. prediksi 30% harus menang ~30% "
                  "dari waktu). Ini yang menentukan layak/tidaknya bertaruh.",
        "tujuan": "Memeriksa apakah probabilitas model dapat dipercaya sebagai "
                  "dasar keputusan.",
        "dampak": "Model terkalibrasi memungkinkan perhitungan value bet yang "
                  "benar. Bila melenceng dari diagonal, probabilitas perlu "
                  "dikalibrasi ulang sebelum dipakai bertaruh.",
        "baca": "Garis putus-putus = sempurna. Titik model yang dekat garis = "
                "terkalibrasi baik. Label 'n' = jumlah sampel di bin tersebut.",
    },
    "backtest": {
        "judul": "Backtest ROI per Strategi",
        "kenapa": "Akurasi prediksi tidak sama dengan keuntungan. Perlu diuji "
                  "apakah mengikuti sinyal benar-benar menghasilkan uang setelah "
                  "margin buku (bookmaker margin).",
        "tujuan": "Mengukur return-on-investment (ROI) tiap strategi pada race "
                  "yang sudah selesai — termasuk kenyataan bila merugi.",
        "dampak": "Menentukan strategi mana yang layak dijalankan; sekaligus "
                  "bukti jujur apakah model mengalahkan baseline (taruh favorit).",
        "baca": "0% = impas. Hijau = untung, merah = rugi. Label memuat jumlah "
                "taruhan (n). Semua strategi negatif = margin pasar lebih besar "
                "dari edge model.",
    },
    "equity": {
        "judul": "Kurva Ekuitas (Equity Curve)",
        "kenapa": "ROI tunggal menyembunyikan perjalanan; kurva ekuitas "
                  "menunjukkan stabilitas dan risiko sebenarnya dari waktu ke waktu.",
        "tujuan": "Melihat bagaimana keuntungan/kerugian menumpuk sepanjang "
                  "rentetan taruhan — mengukur konsistensi, bukan hanya hasil akhir.",
        "dampak": "Kurva menurun tajam = risiko tinggi/drawdown besar meski ROI "
                  "akhir baik. Membantu menilai apakah strategi dapat 'ditahan' "
                  "secara psikologis & modal.",
        "baca": "Sumbu-X = nomor taruhan berurutan; Sumbu-Y = laba kumulatif "
                "dalam unit. Garis datar = stabil; naik/turun tajam = volatil.",
    },
    "odds_winrate": {
        "judul": "Win Rate menurut Bucket Odds",
        "kenapa": "Untuk menilai model, kita harus tahu seberapa informatif "
                  "pasar: apakah favorit (odds rendah) memang lebih sering menang?",
        "tujuan": "Membandingkan tingkat kemenangan nyata per kelompok odds "
                  "dengan probabilitas tersirat pasar.",
        "dampak": "Bila win rate nyata ≈ probabilitas tersirat, pasar efisien → "
                  "edge hanya bisa datang dari model yang lebih baik dari pasar. "
                  "Penyimpangan menandakan peluang sistematis.",
        "baca": "Batang = win rate nyata per bucket odds; garis oranye = "
                "probabilitas tersirat (perkiraan pasar).",
    },
    "barrier": {
        "judul": "Win Rate menurut Posisi Barrier (Gawang)",
        "kenapa": "Posisi start (barrier) secara teori memengaruhi peluang: "
                  "gawang luar menempuh jarak lebih jauh di tikungan.",
        "tujuan": "Menguji apakah barrier benar-benar memengaruhi peluang menang "
                  "pada data ini.",
        "dampak": "Bila pengaruh signifikan, barrier harus jadi fitur model; "
                  "bila tidak, ia bisa diabaikan sehingga model lebih sederhana.",
        "baca": "Sumbu-X = nomor barrier; Sumbu-Y = win rate. 'n' kecil = "
                "kesimpulan untuk barrier itu kurang dapat diandalkan.",
    },
    "data_quality": {
        "judul": "Kualitas Data",
        "kenapa": "Semua analisis di atas hanya sekuat datanya. Menyembunyikan "
                  "masalah data membuat kesimpulan menyesatkan.",
        "tujuan": "Mengukur kelengkapan fitur & hasil, serta menandai keterbatasan "
                  "(mis. odds hilang setelah race selesai).",
        "dampak": "Menentukan seberapa jauh kesimpulan boleh ditarik, dan fitur "
                  "mana yang layak dipercaya. Transparansi ini menjaga kredibilitas.",
        "baca": "Persentase terisi per kolom; nilai rendah = fitur lemah.",
    },
}


def text(key: str) -> str:
    e = EXPLAIN.get(key)
    if not e:
        return ""
    parts = [f"**{e['judul']}**",
             f"- **Kenapa:** {e['kenapa']}",
             f"- **Tujuan:** {e['tujuan']}",
             f"- **Dampak:** {e['dampak']}"]
    if e.get("baca"):
        parts.append(f"- **Cara baca:** {e['baca']}")
    return "\n".join(parts)


def render(key: str, expanded: bool = False, st=None):
    if st is None:
        import streamlit as st  # noqa
    e = EXPLAIN.get(key)
    if not e:
        return
    with st.expander(f"💡 {e['judul']} — Kenapa · Tujuan · Dampak", expanded=expanded):
        st.markdown(
            f"**🔎 Kenapa** — {e['kenapa']}\n\n"
            f"**🎯 Tujuan** — {e['tujuan']}\n\n"
            f"**📈 Dampak** — {e['dampak']}")
        if e.get("baca"):
            st.caption(f"👁️ Cara baca: {e['baca']}")


def audit() -> dict:
    return {k: all(v.get(f) for f in ("kenapa", "tujuan", "dampak"))
            for k, v in EXPLAIN.items()}


if __name__ == "__main__":
    ok = audit()
    print(f"Penjelasan: {len(ok)} | lengkap: {sum(ok.values())}")
    for k, v in ok.items():
        print(f"  {'OK ' if v else 'MISSING'} {k}")
