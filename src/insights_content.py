
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
        {
            "aksi": "Kalibrasi probabilitas model sebelum dipakai untuk keputusan uang",
            "langkah": [
                "Jalankan model logistic regression (numpy) lalu hitung kurva "
                "kalibrasi: bandingkan probabilitas prediksi vs frekuensi menang aktual.",
                "Ukur ROC-AUC 5-fold CV dan Brier score — hanya loloskan model ke "
                "tahap taruhan bila Brier rendah dan ROC-AUC stabil antar fold.",
                "Terapkan koreksi isotonic/Platt scaling bila miscalibrated, "
                "verifikasi ulang kurva setelah koreksi.",
            ],
            "metrik": "Brier score turun & kurva kalibrasi mendekati diagonal; ROC-AUC 5-fold CV konsisten antar fold",
            "pemilik": "Data Scientist (pemilik model)",
        },
        {
            "aksi": "Cari value bet: probabilitas model > probabilitas tersirat odds",
            "langkah": [
                "Untuk tiap runner ambil probabilitas model (terkalibrasi) dan "
                "probabilitas tersirat dari odds (1/odds).",
                "Filter kuda dengan probabilitas model > probabilitas tersirat "
                "di atas ambang margin tertentu (pasar meremehkan).",
                "Cross-check kandidat value bet terhadap analisis win rate vs odds "
                "& vs barrier untuk memastikan edge bukan kebetulan.",
            ],
            "metrik": "Jumlah value bet teridentifikasi & rata-rata selisih (model − implied) per kandidat",
            "pemilik": "Quant Analyst / Strategi Taruhan",
        },
        {
            "aksi": "Backtest strategi di data historis sebelum mempertaruhkan modal nyata",
            "langkah": [
                "Bangun data historis dari Racenet (racenet.com.au) via zero-browser: "
                "curl_cffi + proxy AU + decode Nuxt SSR.",
                "Replay prediksi model atas data historis dan simulasi taruhan pada "
                "tiap kandidat value bet.",
                "Bandingkan ROI strategi model vs baseline favorit pada beberapa "
                "periode terpisah, bukan satu periode tunggal.",
            ],
            "metrik": "ROI per periode, konsistensi tanda ROI, dan selisih ROI vs baseline favorit",
            "pemilik": "Quant Analyst (pemilik backtest)",
        },
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
        {
            "aksi": "Verifikasi fitur penting masuk akal secara domain (form, odds)",
            "langkah": [
                "Ekstrak koefisien/bobot tiap fitur dari model logistic regression "
                "(numpy) dan urutkan berdasarkan kontribusi absolut.",
                "Cocokkan fitur teratas dengan domain horse-racing (form, odds, "
                "barrier) — fitur penting yang tak masuk akal = sinyal data leakage.",
                "Uji ulang ROC-AUC 5-fold CV setelah menandai fitur mencurigakan "
                "untuk melihat apakah performa turun drastis (indikasi leakage).",
            ],
            "metrik": "Kesesuaian fitur teratas dengan domain + perubahan ROC-AUC saat fitur curiga dibuang",
            "pemilik": "Data Scientist (audit fitur)",
        },
        {
            "aksi": "Buang fitur ber-kontribusi nol/negatif untuk mengurangi overfitting",
            "langkah": [
                "Tandai fitur dengan koefisien mendekati nol atau bertanda negatif "
                "yang berlawanan intuisi domain.",
                "Latih ulang model tanpa fitur tersebut, bandingkan ROC-AUC 5-fold "
                "CV dan Brier score sebelum vs sesudah.",
                "Pertahankan penghapusan hanya bila performa CV tidak merosot "
                "(model lebih sederhana & stabil).",
            ],
            "metrik": "Perubahan ROC-AUC 5-fold CV & Brier score sebelum vs sesudah pruning; jumlah fitur berkurang",
            "pemilik": "Data Scientist (pemilik model)",
        },
        {
            "aksi": "Sadari bila 'implied_prob' (pasar) dominan — model hanya meniru pasar",
            "langkah": [
                "Bandingkan besaran kontribusi fitur 'implied_prob' terhadap total "
                "kontribusi seluruh fitur.",
                "Latih model tanpa 'implied_prob' dan ukur penurunan ROC-AUC — "
                "model yang bergantung penuh akan kolaps.",
                "Bila pasar dominan, turunkan ekspektasi nilai tambah dan fokus "
                "pada segmen (race/odds bucket) tempat model menyimpang dari pasar.",
            ],
            "metrik": "Porsi kontribusi fitur implied_prob vs fitur lain & selisih ROC-AUC model dengan/tanpa fitur pasar",
            "pemilik": "Quant Analyst (riset edge)",
        },
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
        {
            "aksi": "Pakai model hanya jika kurva kalibrasi dekat garis diagonal",
            "langkah": [
                "Plot kurva kalibrasi: probabilitas prediksi (sumbu X) vs frekuensi "
                "menang aktual (sumbu Y) pada data out-of-fold.",
                "Bagi prediksi ke bucket probabilitas (mis. 0–10%, 10–20%, ...) dan "
                "hitung deviasi tiap bucket terhadap garis diagonal.",
                "Tetapkan kriteria lolos (mis. deviasi maksimum antar bucket di bawah "
                "ambang) sebelum model boleh dipakai untuk keputusan uang.",
            ],
            "metrik": "Deviasi maksimum bucket terhadap diagonal & Brier score keseluruhan",
            "pemilik": "Data Scientist (validasi model)",
        },
        {
            "aksi": "Terapkan koreksi (isotonic/Platt scaling) bila miscalibrated",
            "langkah": [
                "Identifikasi pola miscalibration: overconfident (kurva di bawah "
                "diagonal) atau underconfident (di atas diagonal).",
                "Latih kalibrator isotonic regression atau Platt scaling pada "
                "prediksi out-of-fold (bukan data latih) untuk menghindari leakage.",
                "Verifikasi ulang kurva kalibrasi dan Brier score setelah koreksi; "
                "simpan kalibrator bersama artefak model.",
            ],
            "metrik": "Penurunan Brier score & deviasi diagonal setelah koreksi",
            "pemilik": "Data Scientist (pemilik kalibrator)",
        },
        {
            "aksi": "Baru setelah terkalibrasi, hitung value bet yang dapat dipercaya",
            "langkah": [
                "Ambil probabilitas model yang sudah terkalibrasi sebagai input "
                "perhitungan ekspektasi keuntungan.",
                "Hitung ekspektasi = p_model × (odds − 1) − (1 − p_model) per kandidat "
                "dan pilih hanya yang positif di atas margin bookmaker.",
                "Validasi kandidat terhadap analisis win rate vs odds untuk memastikan "
                "value tidak berasal dari bucket efisien.",
            ],
            "metrik": "Ekspektasi keuntungan positif per taruhan & konsistensi dengan win rate vs odds",
            "pemilik": "Quant Analyst / Strategi Taruhan",
        },
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
        {
            "aksi": "Jalankan hanya strategi dengan ROI positif yang konsisten antar periode",
            "langkah": [
                "Bangun data historis Racenet via zero-browser (curl_cffi + proxy AU "
                "+ decode Nuxt SSR) lalu bagi ke beberapa periode waktu terpisah.",
                "Hitung ROI strategi model per periode dan catat tanda (positif/negatif) "
                "tiap periode, bukan hanya total gabungan.",
                "Loloskan strategi hanya bila ROI positif bertahan di mayoritas "
                "periode; bandingkan dengan baseline favorit yang ROI-nya negatif.",
            ],
            "metrik": "ROI per periode, jumlah periode ROI positif, & selisih ROI vs baseline favorit (−36.5%)",
            "pemilik": "Quant Analyst (pemilik backtest)",
        },
        {
            "aksi": "Waspadai ROI tinggi dengan sedikit taruhan (bisa kebetulan)",
            "langkah": [
                "Catat jumlah taruhan (n) tiap hasil strategi bersama angka ROI-nya.",
                "Hitung interval kepercayaan (bootstrap) untuk ROI — sampel kecil "
                "menghasilkan rentang sangat lebar yang menembus nol.",
                "Tolak klaim edge bila ROI tinggi tidak stabil saat n diperbesar atau "
                "saat diuji pada periode lain.",
            ],
            "metrik": "Jumlah taruhan (n), interval kepercayaan ROI (bootstrap), & stabilitas ROI saat n bertambah",
            "pemilik": "Quant Analyst (validasi statistik)",
        },
        {
            "aksi": "Hitung biaya nyata (margin bookmaker), bukan hanya odds mentah",
            "langkah": [
                "Konversi odds ke probabilitas tersirat dan hitung overround "
                "(jumlah implied prob seluruh runner > 100%) sebagai margin bookmaker.",
                "Kurangi margin tersebut dari ekspektasi setiap taruhan sebelum "
                "menghitung ROI bersih.",
                "Revisi hasil backtest: strategi yang hanya unggul sebelum margin "
                "harus dianggap tidak profitable.",
            ],
            "metrik": "Overround/margin per balapan & ROI bersih setelah margin",
            "pemilik": "Quant Analyst / Strategi Taruhan",
        },
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
        {
            "aksi": "Cari bucket odds di mana win rate nyata > implied (ada value)",
            "langkah": [
                "Kelompokkan runner ke bucket odds (mis. 1–2, 2–5, 5–10, 10–20, >20) "
                "dan hitung win rate aktual tiap bucket.",
                "Bandingkan win rate aktual dengan probabilitas tersirat rata-rata "
                "bucket; tandai bucket dengan selisih positif signifikan.",
                "Fokuskan pencarian value bet pada bucket unggulan dan verifikasi "
                "dengan kurva kalibrasi model di rentang odds tersebut.",
            ],
            "metrik": "Selisih (win rate aktual − implied) per bucket odds & jumlah bucket surplus",
            "pemilik": "Quant Analyst (analisis edge)",
        },
        {
            "aksi": "Bila semua bucket efisien, kurangi frekuensi bertaruh atau cari pasar kurang efisien",
            "langkah": [
                "Uji seluruh bucket: bila win rate ≈ implied (dalam margin sampling), "
                "pasar tergolong efisien.",
                "Turunkan volume taruhan ke hanya kondisi penyimpangan jelas, atau "
                "alihkan fokus ke segmen (race/track) dengan overround lebih rendah.",
                "Pantau ulang secara berkala karena efisiensi pasar dapat berubah "
                "seiring waktu.",
            ],
            "metrik": "Jumlah bucket efisien vs surplus & perubahan volume taruhan yang dialokasikan",
            "pemilik": "Strategi Taruhan / Pemilik modal",
        },
        {
            "aksi": "Jadikan analisis ini filter: bertaruh hanya saat ada penyimpangan jelas",
            "langkah": [
                "Terapkan win rate vs odds sebagai gatekeeper: blokir taruhan pada "
                "bucket efisien.",
                "Izinkan taruhan hanya bila model menunjukkan selisih positif di "
                "bucket yang juga surplus secara historis.",
                "Rekam setiap taruhan yang lolos filter untuk mengukur performa "
                "gatekeeper dari waktu ke waktu.",
            ],
            "metrik": "Presisi filter (win rate taruhan lolos filter) & ROI taruhan yang lolos",
            "pemilik": "Strategi Taruhan (penanggung jawab eksekusi)",
        },
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
        {
            "aksi": "Bila signifikan: jadikan barrier fitur & manfaatkan posisi diuntungkan yang diabaikan pasar",
            "langkah": [
                "Hitung win rate per posisi barrier dan uji signifikansi perbedaannya "
                "(mis. chi-square / interval kepercayaan antar posisi).",
                "Bila berbeda nyata, masukkan barrier sebagai fitur model dan latih "
                "ulang, lalu cek perubahan ROC-AUC 5-fold CV.",
                "Cari posisi barrier dengan win rate tinggi namun odds-nya tidak "
                "menyesuaikan — kandidat value yang pasar abaikan.",
            ],
            "metrik": "Signifikansi win rate antar barrier, perubahan ROC-AUC 5-fold CV, & selisih (win rate − implied) per posisi",
            "pemilik": "Data Scientist & Quant Analyst (fitur + edge)",
        },
        {
            "aksi": "Bila tidak signifikan: jangan buang kompleksitas model untuk fitur ini",
            "langkah": [
                "Bila uji signifikansi gagal menolak hipotesis nol (win rate antar "
                "barrier ≈ sama), tandai barrier sebagai fitur lemah.",
                "Latih model dengan & tanpa barrier dan bandingkan ROC-AUC 5-fold CV "
                "— bila tak ada perbaikan, keluarkan fitur.",
                "Dokumentasikan keputusan agar tak diuji ulang tanpa alasan.",
            ],
            "metrik": "p-value uji beda win rate & selisih ROC-AUC 5-fold CV dengan/tanpa fitur barrier",
            "pemilik": "Data Scientist (pemilik model)",
        },
        {
            "aksi": "Verifikasi 'teori' dengan data — jangan asumsikan pengaruh tanpa bukti",
            "langkah": [
                "Tetapkan ambang signifikansi (mis. p < 0.05) dan ukuran sampel "
                "minimal sebelum menilai barrier.",
                "Hitung efek praktis (selisih win rate absolut terbesar antar posisi) "
                "selain signifikansi statistik.",
                "Baru putuskan memasukkan/mengabaikan barrier berdasarkan bukti "
                "kuantitatif, bukan asumsi domain.",
            ],
            "metrik": "p-value, ukuran sampel per posisi, & selisih win rate absolut maksimum antar barrier",
            "pemilik": "Data Scientist (keputusan berbasis data)",
        },
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
        {
            "aksi": "Fokuskan value-betting pada race dengan sebaran LEBAR, bukan race merata",
            "langkah": [
                "Hitung sebaran (rentang/IQR) probabilitas prediksi per race dari "
                "output model logistic regression.",
                "Tandai race dengan sebaran lebar (ada kuda underrated) sebagai "
                "prioritas dan sisihkan race merata ber-sebaran sempit.",
                "Pada race prioritas, cari kuda dengan probabilitas model > implied "
                "odds sebagai kandidat value bet.",
            ],
            "metrik": "IQR/rentang probabilitas per race & jumlah value bet yang lolos di race prioritas",
            "pemilik": "Quant Analyst / Strategi Taruhan",
        },
        {
            "aksi": "Waspadai race dengan satu pencilan ekstrem (risiko konsentrasi tinggi)",
            "langkah": [
                "Deteksi race dengan pencilan probabilitas ekstrem (satu kuda jauh di "
                "atas sisanya, mis. > 2× median).",
                "Bandingkan keyakinan model versus odds pasar — jika pasar tidak "
                "sekeyakinan model, curigai overconfidence.",
                "Batasi ukuran taruhan pada race berpencilan tunggal untuk mengelola "
                "risiko konsentrasi.",
            ],
            "metrik": "Jumlah race berpencilan ekstrem & perbedaan (probabilitas model − implied) kuda dominan",
            "pemilik": "Manajer Risiko / Strategi Taruhan",
        },
        {
            "aksi": "Kalibrasi ulang bila banyak track menunjukkan kotak sempit",
            "langkah": [
                "Hitung porsi track dengan sebaran sempit (model kehilangan daya "
                "pisah) pada boxplot.",
                "Periksa kurva kalibrasi pada track-track tersebut untuk mengonfirmasi "
                "penurunan daya pisah.",
                "Bila terkonfirmasi, latih ulang/terapkan kalibrasi isotonic atau "
                "Platt scaling dan evaluasi ulang.",
            ],
            "metrik": "Porsi track ber-sebaran sempit, deviasi kalibrasi pada track itu, & Brier score sebelum/sesudah kalibrasi ulang",
            "pemilik": "Data Scientist (validasi & kalibrasi)",
        },
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
        {
            "aksi": "Ukur strategi dari SELISIH terhadap baseline favorit, bukan ROI absolut",
            "langkah": [
                "Hitung ROI baseline favorit (mendekati −36.5%) sebagai titik awal "
                "referensi pasar.",
                "Hitung ROI strategi model (mendekati −4.9%) dan selisihnya terhadap "
                "baseline via waterfall.",
                "Nilai keberhasilan model dari selisih positif ini, bukan dari tanda "
                "ROI absolut yang tetap negatif karena margin bookmaker.",
            ],
            "metrik": "Selisih ROI model vs baseline favorit (mis. −4.9% − (−36.5%)) dalam poin persentase",
            "pemilik": "Quant Analyst (pemilik evaluasi strategi)",
        },
        {
            "aksi": "Jika keunggulan model menghilang pada sampel lebih besar, perlakukan sebagai kebetulan",
            "langkah": [
                "Perbesar sampel data historis dan hitung ulang selisih ROI model vs "
                "baseline.",
                "Uji apakah selisih tetap stabil (interval kepercayaan tidak menembus "
                "nol) atau menyusut mendekati nol.",
                "Bila selisih menghilang, turunkan klasifikasi keunggulan dari "
                "'terbukti' menjadi 'belum terbukti'.",
            ],
            "metrik": "Perubahan selisih ROI saat sampel diperbesar & interval kepercayaan selisih",
            "pemilik": "Quant Analyst (validasi statistik)",
        },
        {
            "aksi": "Perluas sampel sebelum mempercayai ROI positif mana pun",
            "langkah": [
                "Tetapkan ukuran sampel minimal (jumlah taruhan/race) sebelum ROI "
                "boleh dianggap bermakna, mengingat strategi berbasis margin tipis.",
                "Jalankan backtest pada periode terpisah (in-sample vs out-of-sample) "
                "untuk menguji konsistensi.",
                "Hindari mengalokasikan modal nyata selama sampel masih kecil dan "
                "margin bookmaker belum dikurangi.",
            ],
            "metrik": "Jumlah taruhan (n) & konsistensi tanda ROI antar periode sampel",
            "pemilik": "Manajer Risiko / Pemilik modal",
        },
    ],
    risiko=(
        "ROI positif pada sampel kecil mudah menyesatkan. Menganggapnya sebagai "
        "sinyal 'siap taruhan uang nyata' berisiko kerugian besar. Bukan saran "
        "taruhan — analisis edukasional."),
    tingkat="tinggi",
)
