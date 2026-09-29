
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


# --------------------------------------------------------------------------
# Chart ECharts (v2) — insight & rekomendasi.
# --------------------------------------------------------------------------

register(
    "echarts_boxplot",
    kesimpulan=(
        "Boxplot probabilitas prediksi per track mengungkap KEPERCAYAAN model: "
        "kotak sempit & rendah = field merata (model ragu, tak ada favorit kuat); "
        "kotak tinggi dengan pencilan = ada kuda dominan yang diprediksi jauh di "
        "atas sisanya. Bentuk ini menentukan seberapa 'tegas' sebuah race."),
    rekomendasi=[
        "Fokuskan value-betting pada race dengan sebaran LEBAR (ada kuda "
        "underrated) alih-alih race merata yang sulit diprediksi.",
        "Waspadai race dengan satu pencilan ekstrem — model sangat yakin, tetapi "
        "satu kuda = risiko konsentrasi tinggi.",
        "Kalibrasi ulang bila banyak track menunjukkan kotak sempit (model "
        "kehilangan daya pisah).",
    ],
    risiko=(
        "Bertaruh di race merata (sebaran sempit) berarti bersaing dengan "
        "kepastian rendah — ROI cenderung buruk. Sebaliknya, terlalu percaya pada "
        "satu pencilan bisa hancur bila kuda itu gagal. Backtest tetap wajib."),
    tingkat="sedang",
)

register(
    "echarts_waterfall",
    kesimpulan=(
        "Waterfall menjembatani ROI baseline 'taruhan favorit' (negatif) ke ROI "
        "'pilihan model' (positif): bar merah = titik awal merugi, bar hijau = "
        "nilai tambah dari seleksi model, bar biru = hasil akhir. Ini "
        "memvisualisasikan bahwa KEUNGGULAN UTAMA bukan menang besar, melainkan "
        "menghindari kerugian besar."),
    rekomendasi=[
        "Ukur strategi dari SELISIH terhadap baseline favorit, bukan ROI absolut "
        "— baseline negatif itu ekspektasi pasar.",
        "Jika keunggulan model menghilang pada sampel lebih besar, perlakukan "
        "sebagai kebetulan (model belum terbukti).",
        "Perluas sampel sebelum mempercayai ROI positif mana pun — margin "
        "bookmaker tetap lawan utama.",
    ],
    risiko=(
        "ROI positif pada sampel kecil mudah menyesatkan. Menganggapnya sebagai "
        "sinyal 'siap taruhan uang nyata' berisiko kerugian besar. Bukan saran "
        "taruhan — analisis edukasional."),
    tingkat="tinggi",
)
