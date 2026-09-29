
# ---------------------------------------------------------------------------
# KONTEN INSIGHT — Horse Racing Analytics
# Sudut pandang: pemodal/trader yang memutuskan strategi taruhan berbasis model.
# ---------------------------------------------------------------------------
from insight import register

register(
    "predictions",
    kesimpulan=(
        "Model memprediksi probabilitas menang tiap kuda per balapan. Kualitas "
        "model menentukan apakah prediksi bisa dipakai mencari value bet — "
        "akurasi tinggi TIDAK otomatis berarti untung."),
    rekomendasi=[
        "Gunakan probabilitas model HANYA setelah dikalibrasi — jangan pakai "
        "skor mentah untuk keputusan uang.",
        "Cari 'value bet': kuda dengan probabilitas model > probabilitas tersirat "
        "odds (pasar meremehkan) — bukan sekadar kuda terkuat.",
        "Uji strategi di data historis (backtest) sebelum mempertaruhkan modal nyata.",
    ],
    risiko=(
        "Bertaruh pada favorit model tanpa cek kalibrasi = kalah, karena pasar "
        "biasanya sudah efisien di favorit. Modal tergerus oleh favorit yang "
        "odds-nya tidak sepadan."),
    tingkat="tinggi",
)

register(
    "feature_importance",
    kesimpulan=(
        "Model 'black-box' tak dapat dipercaya. Feature importance mengungkap "
        "sinyal apa yang benar-benar dipakai model — memisahkan sinyal nyata dari "
        "kebetulan statistik."),
    rekomendasi=[
        "Verifikasi fitur penting MASUK AKAL secara domain (form, odds) — bila "
        "tidak, curigai data leakage.",
        "Buang fitur ber-kontribusi nol/negatif untuk mengurangi overfitting.",
        "Bila 'implied_prob' (pasar) dominan, sadari model hanya meniru pasar — "
        "nilai tambahnya terbatas.",
    ],
    risiko=(
        "Model bergantung pada fitur tak masuk akal (kebocoran data) akan tampak "
        "hebat di backtest tapi gagal total saat taruhan nyata."),
    tingkat="tinggi",
)

register(
    "calibration",
    kesimpulan=(
        "Probabilitas yang baik bukan hanya mengurutkan, tapi AKURAT: kuda yang "
        "diprediksi 30% harus menang ~30% dari waktu. Kurva kalibrasi menguji "
        "kejujuran probabilitas model."),
    rekomendasi=[
        "Pakai model HANYA jika kurva kalibrasi dekat garis diagonal.",
        "Bila miscalibrated, terapkan koreksi (isotonic/Platt scaling) sebelum "
        "menghitung ekspektasi keuntungan.",
        "Baru setelah terkalibrasi, hitung value bet yang dapat dipercaya.",
    ],
    risiko=(
        "Model miscalibrated membuat perhitungan 'value' salah. Kamu bisa mengira "
        "menemukan peluang emas padahal probabilitas sesungguhnya jauh berbeda — "
        "kerugian sistematis."),
    tingkat="kritis",
)

register(
    "backtest",
    kesimpulan=(
        "Akurasi prediksi ≠ keuntungan. Backtest menguji apakah strategi benar-"
        "benar menghasilkan ROI positif setelah memperhitungkan odds — ujian "
        "sebenarnya sebelum taruhan nyata."),
    rekomendasi=[
        "Jalankan HANYA strategi dengan ROI positif yang konsisten di beberapa "
        "periode, bukan yang menang sekali.",
        "Waspadai ROI tinggi dengan sedikit taruhan (bisa kebetulan).",
        "Hitung biaya nyata (margin bandar), bukan hanya odds mentah.",
    ],
    risiko=(
        "Backtest yang overfitting ke masa lalu memberi keyakinan palsu. Strategi "
        "'juara' di data historis sering gagal total di taruhan nyata."),
    tingkat="kritis",
)

register(
    "odds_winrate",
    kesimpulan=(
        "Win rate nyata per bucket odds menunjukkan efisiensi pasar. Bila win "
        "rate ≈ probabilitas tersirat odds, pasar efisien → sulit mendapat "
        "keuntungan sistematis."),
    rekomendasi=[
        "Cari bucket odds di mana win rate nyata > implied — di situ ada value.",
        "Bila semua bucket efisien, kurangi frekuensi bertaruh atau cari pasar "
        "yang kurang efisien.",
        "Jadikan analisis ini filter: bertaruh hanya saat ada penyimpangan jelas.",
    ],
    risiko=(
        "Bertaruh sistematis di pasar efisien = membayar margin bandar tanpa "
        "edge. Modal tergerus perlahan, tampak seperti 'sekadar sial'."),
    tingkat="tinggi",
)

register(
    "barrier",
    kesimpulan=(
        "Posisi start (barrier) secara teori memengaruhi peluang. Bila win rate "
        "berbeda nyata antar posisi, barrier fitur penting; bila tidak, "
        "pengaruhnya dapat diabaikan."),
    rekomendasi=[
        "Bila signifikan: masukkan barrier sebagai fitur & manfaatkan peluang pada "
        "posisi diuntungkan yang diabaikan pasar.",
        "Bila tidak signifikan: jangan buang kompleksitas model untuk fitur ini.",
        "Verifikasi 'teori' dengan data — jangan asumsikan pengaruh tanpa bukti.",
    ],
    risiko=(
        "Mengabaikan faktor berpengaruh nyata (atau menambah yang tidak) melemahkan "
        "model. Keputusan berbasis asumsi tanpa bukti = edge yang hilang."),
    tingkat="sedang",
)
