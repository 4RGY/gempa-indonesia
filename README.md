# Gempa Indonesia

Analisis katalog gempa terkini dari data terbuka BMKG. Semua angka dihitung ulang setiap kali
pipeline dijalankan, tidak ada yang ditulis manual.

Sumber data: [BMKG Open Data](https://data.bmkg.go.id/) (`gempaterkini.json`, `gempadirasakan.json`).

## Snapshot terakhir

<!-- RINGKASAN:START -->
**Data diambil:** 2026-10-20 18:40 UTC  
**Gempa dalam katalog:** 28 kejadian (15 dari katalog M5+, 13 dirasakan)  
**Magnitudo:** rata-rata 4,64, terbesar M6,1  
**Kedalaman median:** 10,0 km (89,3% gempa dangkal)  
**b-value Gutenberg-Richter:** 1,55 +- 0,49 (indikatif, sampel kecil)  
**Total energi seismik:** 0,26 PJ (setara 62.137 ton TNT)  
**Berpotensi tsunami:** 0 kejadian
<!-- RINGKASAN:END -->

## Yang dihitung

| Bagian | Isi |
|---|---|
| Pembersihan | parser khusus field teks BMKG (`5,4` / `74 km` / `8.09 LS` / `Tidak berpotensi tsunami`) |
| Statistik dasar | jumlah, magnitudo rata-rata dan median, kedalaman, porsi gempa dangkal |
| Seismisitas | b-value Gutenberg-Richter dengan estimator Aki-Utsu, Mc maximum curvature |
| Energi | konversi `log10 E = 4.8 + 1.5 M`, total joule, setara TNT, pangsa gempa terbesar |
| Waktu | jeda antar gempa (median, rata-rata, ekstrem) |
| Spasial | sebaran episentrum, zona terbanyak dari teks wilayah BMKG |

## Output

```
outputs/
  gempa_bersih.csv              katalog bersih siap analisis
  ringkasan.json                semua metrik dalam bentuk mesin
  laporan.md                    laporan siap baca
  01_timeline_magnitudo.png
  02_kedalaman_vs_magnitudo.png
  03_distribusi_magnitudo.png
  04_peta_episentrum.png
```

`README.md` bagian snapshot juga ikut diperbarui otomatis oleh pipeline.

## Gambar

![Garis waktu magnitudo](outputs/01_timeline_magnitudo.png)

![Kedalaman vs magnitudo](outputs/02_kedalaman_vs_magnitudo.png)

## Cara jalan

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

gempa-indonesia                  # atau: python -m gempa_indonesia.cli
pytest
```

Opsi CLI: `--outdir outputs`, `--no-charts`, `--readme README.md`.

## Struktur

```
src/gempa_indonesia/
  fetch.py     ambil JSON BMKG dengan retry
  parse.py     normalisasi field teks jadi angka
  analysis.py  statistik, b-value, neraca energi
  charts.py    empat gambar matplotlib
  report.py    laporan markdown dan update README
  cli.py       orkestrasi satu perintah
tests/         tes parser dan analisis, tanpa jaringan
```

## Keterbatasan

- Katalog publik BMKG hanya memuat gempa M5,0 ke atas plus gempa yang dirasakan. Ini bukan
  katalog lengkap, jadi b-value di sini tidak sebanding dengan studi regional jangka panjang.
- Provinsi diambil dari teks wilayah BMKG dengan pencocokan kode provinsi (`ACEH`, `SUMBAR`,
  `NTT`, dan seterusnya). Kalau BMKG menulis nama wilayah tanpa kode provinsi, baris itu masuk
  ke kelompok "tidak terdeteksi" alih-alih ditebak.
- Data diambil sekali per eksekusi. Untuk peringatan resmi, selalu cek BMKG.

## Lisensi

MIT. Data tetap milik BMKG.
