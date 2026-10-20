"""Transformasi dan analisis katalog gempa BMKG."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from .parse import normalize

KOLOM = [
    "sumber", "waktu_utc", "tanggal", "jam_wib", "lintang", "bujur",
    "magnitude", "kedalaman_km", "wilayah", "potensi_tsunami", "dirasakan",
]

BATAS_DANGKAL_KM = 70
BATAS_MENENGAH_KM = 300

# Kode provinsi yang biasa muncul di akhir teks wilayah BMKG.
PROVINSI = {
    "ACEH": "Aceh", "SUMUT": "Sumatera Utara", "SUMBAR": "Sumatera Barat",
    "RIAU": "Riau", "KEPRI": "Kepulauan Riau", "JAMBI": "Jambi",
    "SUMSEL": "Sumatera Selatan", "BABEL": "Bangka Belitung", "BENGKULU": "Bengkulu",
    "LAMPUNG": "Lampung", "BANTEN": "Banten", "JAKARTA": "DKI Jakarta",
    "JABAR": "Jawa Barat", "JATENG": "Jawa Tengah", "JOGJA": "DI Yogyakarta",
    "JATIM": "Jawa Timur", "BALI": "Bali", "NTB": "Nusa Tenggara Barat",
    "NTT": "Nusa Tenggara Timur", "KALBAR": "Kalimantan Barat",
    "KALTENG": "Kalimantan Tengah", "KALSEL": "Kalimantan Selatan",
    "KALTIM": "Kalimantan Timur", "KALTARA": "Kalimantan Utara",
    "SULUT": "Sulawesi Utara", "GORONTALO": "Gorontalo",
    "SULTENG": "Sulawesi Tengah", "SULBAR": "Sulawesi Barat",
    "SULSEL": "Sulawesi Selatan", "SULTRA": "Sulawesi Tenggara",
    "MALUKU": "Maluku", "MALUKUUTARA": "Maluku Utara",
    "PAPUABARATDAYA": "Papua Barat Daya", "PAPUABARAT": "Papua Barat",
    "PAPUAPEGUNUNGAN": "Papua Pegunungan", "PAPUATENGAH": "Papua Tengah",
    "PAPUASELATAN": "Papua Selatan", "PAPUA": "Papua",
}
# Cek dari yang paling panjang supaya MALUKUUTARA tidak tertangkap MALUKU.
_KUNCI_PROVINSI = sorted(PROVINSI, key=len, reverse=True)


def build_dataframe(raw: dict[str, list[dict[str, Any]]]) -> pd.DataFrame:
    """Gabungkan semua sumber BMKG jadi satu tabel bersih tanpa duplikat."""
    baris: list[dict[str, Any]] = []
    for sumber, records in raw.items():
        for rec in records:
            try:
                baris.append(normalize(rec, sumber))
            except (KeyError, ValueError):
                continue  # record cacat dilewati, bukan bikin pipeline mati
    df = pd.DataFrame(baris, columns=KOLOM)
    if df.empty:
        return df
    df = df.drop_duplicates(subset=["waktu_utc", "lintang", "bujur", "magnitude"])
    df = df.sort_values("waktu_utc").reset_index(drop=True)
    df["kategori_kedalaman"] = df["kedalaman_km"].map(kategori_kedalaman)
    df["provinsi"] = [
        provinsi(f"{w} {d or ''}") for w, d in zip(df["wilayah"], df["dirasakan"])
    ]
    return df


def kategori_kedalaman(km: float) -> str:
    if km < BATAS_DANGKAL_KM:
        return "dangkal"
    if km <= BATAS_MENENGAH_KM:
        return "menengah"
    return "dalam"


def provinsi(wilayah: str) -> str:
    """Tebak provinsi dari teks wilayah BMKG, mis. 'CALANG-ACEHJAYA' -> 'Aceh'.

    BMKG menulis wilayah sebagai teks bebas, jadi ini pencocokan kode provinsi
    yang lazim dipakai di akhir deskripsi. Bisa gagal kalau formatnya beda,
    karena itu teks asli selalu disimpan di kolom `wilayah`.
    """
    teks = (wilayah or "").upper()
    # Prioritaskan segmen terakhir setelah tanda hubung, mis. 'CALANG-ACEHJAYA'
    segmen = "".join(ch for ch in teks.split("-")[-1] if ch.isalnum())
    for kunci in _KUNCI_PROVINSI:
        if kunci in segmen:
            return PROVINSI[kunci]
    # Fallback: cocokkan per kata supaya 'BALIKPAPAN' tidak dianggap 'BALI'
    kata = {k for k in "".join(ch if ch.isalnum() else " " for ch in teks).split()}
    for kunci in _KUNCI_PROVINSI:
        if kunci in kata:
            return PROVINSI[kunci]
    return "Tidak diketahui"


def _statistik(series: pd.Series) -> dict[str, Any]:
    return {
        "rata_rata": round(float(series.mean()), 2),
        "median": round(float(series.median()), 2),
        "maks": round(float(series.max()), 1),
        "min": round(float(series.min()), 1),
    }


def ringkasan(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {"jumlah": 0}
    terbesar = df.loc[df["magnitude"].idxmax()]
    return {
        "jumlah": int(len(df)),
        "jumlah_katalog_m5": int((df["sumber"] == "gempaterkini").sum()),
        "jumlah_dirasakan": int((df["sumber"] == "gempadirasakan").sum()),
        "periode_mulai_utc": df["waktu_utc"].min().isoformat(),
        "periode_akhir_utc": df["waktu_utc"].max().isoformat(),
        "magnitudo": _statistik(df["magnitude"]),
        "kedalaman": _statistik(df["kedalaman_km"]),
        "porsi_dangkal_persen": round(float((df["kategori_kedalaman"] == "dangkal").mean() * 100), 1),
        "gempa_berpotensi_tsunami": int(df["potensi_tsunami"].sum()),
        "gempa_terbesar": {
            "waktu_utc": terbesar["waktu_utc"].isoformat(),
            "magnitude": float(terbesar["magnitude"]),
            "wilayah": terbesar["wilayah"],
            "kedalaman_km": float(terbesar["kedalaman_km"]),
            "provinsi": terbesar["provinsi"],
        },
        "provinsi_terbanyak": df.loc[df["provinsi"] != "Tidak diketahui", "provinsi"]
        .value_counts().head(6).to_dict(),
        "tanpa_provinsi": int((df["provinsi"] == "Tidak diketahui").sum()),
        "sebaran_magnitudo": {f"M{k}": int(v) for k, v in
                             df["magnitude"].round(1).value_counts().sort_index().items()},
        "sebaran_kedalaman": df["kategori_kedalaman"].value_counts().to_dict(),
    }


def b_value(df: pd.DataFrame, mc: float | None = None) -> dict[str, Any]:
    """b-value Gutenberg-Richter dengan estimator Aki-Utsu (MLE).

    b = log10(e) / (mean(M) - Mc)

    Katalog BMKG yang dipakai hanya memuat gempa M >= 5.0, jadi magnitudo
    kelengkapan diestimasi dengan maximum curvature (Mc = Mmin + 0.2). Katalog
    sependek ini membuat galat baku besar, jadi nilainya indikatif, bukan angka
    yang bisa dibandingkan dengan studi regional jangka panjang.
    """
    mag = df["magnitude"].dropna().to_numpy()
    if mag.size < 10:
        return {"tersedia": False, "alasan": "data kurang dari 10 gempa"}
    mmin = float(np.min(mag))
    mc_estimasi = float(mc if mc is not None else round(mmin + 0.2, 1))
    subset = mag[mag >= mc_estimasi]
    if subset.size < 10:
        return {"tersedia": False, "alasan": "sampel di atas Mc terlalu sedikit"}
    mean_m = float(np.mean(subset))
    if mean_m <= mc_estimasi:
        return {"tersedia": False, "alasan": "rata-rata magnitudo di bawah Mc"}
    b = math.log10(math.e) / (mean_m - mc_estimasi)
    error = b / math.sqrt(subset.size)
    return {
        "tersedia": True,
        "b_value": round(b, 3),
        "standar_error": round(error, 3),
        "mc": mc_estimasi,
        "n_dipakai": int(subset.size),
        "magnitudo_rata_rata": round(mean_m, 2),
        "metode": "Aki-Utsu MLE, Mc maximum curvature",
        "stabil": bool(subset.size >= 50 and error < 0.2),
    }


def energi_joule(magnitude: float) -> float:
    """Energi seismik dari magnitudo (Gutenberg-Richter): log10 E = 4.8 + 1.5 M."""
    return 10 ** (4.8 + 1.5 * magnitude)


def neraca_energi(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {}
    energi = df["magnitude"].map(energi_joule)
    total = float(energi.sum())
    terbesar = float(energi.max())
    return {
        "total_joule": total,
        "total_ton_tnt": round(total / 4.184e9, 1),
        "pangsa_gempa_terbesar_persen": round(terbesar / total * 100, 1),
        "setara_bom_atom_hiroshima": round(total / 6.276e13, 2),
    }


def statistik_jeda(df: pd.DataFrame) -> dict[str, Any]:
    if len(df) < 3:
        return {}
    jeda = df["waktu_utc"].diff().dropna().dt.total_seconds() / 3600
    return {
        "jeda_median_jam": round(float(jeda.median()), 1),
        "jeda_rata_rata_jam": round(float(jeda.mean()), 1),
        "jeda_terpendek_jam": round(float(jeda.min()), 1),
        "jeda_terpanjang_jam": round(float(jeda.max()), 1),
    }


def korelasi_kedalaman_magnitudo(df: pd.DataFrame) -> float | None:
    if len(df) < 5:
        return None
    r = df["kedalaman_km"].corr(df["magnitude"])
    return None if pd.isna(r) else round(float(r), 3)
