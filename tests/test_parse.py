"""Tes parser dan analisis. Tidak menyentuh jaringan."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from gempa_indonesia import analysis
from gempa_indonesia.parse import (
    parse_bujur,
    parse_datetime_utc,
    parse_depth_km,
    parse_lintang,
    parse_tsunami,
    normalize,
)


CONTOH = {
    "Tanggal": "20 Okt 2026",
    "Jam": "23:29:35 WIB",
    "DateTime": "2026-10-20T16:29:35+00:00",
    "Coordinates": "3.79,95.72",
    "Lintang": "3.79 LU",
    "Bujur": "95.72 BT",
    "Magnitude": "5.4",
    "Kedalaman": "74 km",
    "Wilayah": "59 km BaratDaya MEULABOH-ACEHBARAT",
    "Potensi": "Tidak berpotensi tsunami",
}


def test_parse_lintang_bujur_arah():
    assert parse_lintang("3.79 LU") == 3.79
    assert parse_lintang("8.09 LS") == -8.09
    assert parse_bujur("95.72 BT") == 95.72
    assert parse_bujur("110.10 BB") == -110.10


def test_parse_kedalaman_dan_magnitudo():
    assert parse_depth_km("74 km") == 74.0
    assert parse_depth_km("10 km") == 10.0
    assert analysis.kategori_kedalaman(74) == "menengah"
    assert analysis.kategori_kedalaman(10) == "dangkal"
    assert analysis.kategori_kedalaman(500) == "dalam"


def test_parse_tsunami():
    assert parse_tsunami("Tidak berpotensi tsunami") is False
    assert parse_tsunami("Berpotensi tsunami") is True
    assert parse_tsunami("Berpotensi TSUNAMI") is True
    assert parse_tsunami(None) is False


def test_parse_datetime_utc():
    dt = parse_datetime_utc("2026-10-20T16:29:35+00:00")
    assert dt.year == 2026 and dt.hour == 16
    assert dt.tzinfo is not None


def test_normalize_lengkap():
    row = normalize(CONTOH, "gempaterkini")
    assert row["magnitude"] == 5.4
    assert row["kedalaman_km"] == 74.0
    assert row["lintang"] == 3.79
    assert row["bujur"] == 95.72
    assert row["potensi_tsunami"] is False


def test_provinsi_dari_teks_bmkg():
    assert analysis.provinsi("68 km BaratDaya CALANG-ACEHJAYA") == "Aceh"
    assert analysis.provinsi("14 km BaratDaya KODI-SUMBABARATDAYA-NTT") == "Nusa Tenggara Timur"
    assert analysis.provinsi("230 km BaratLaut TAHUNA-KEP.SANGIHE-SULUT") == "Sulawesi Utara"
    assert analysis.provinsi("Pusat gempa berada di laut 59 km barat daya Meulaboh") == "Tidak diketahui"
    assert analysis.provinsi("") == "Tidak diketahui"


def test_energi_naik_31_6_kali_per_magnitudo():
    e1 = analysis.energi_joule(5.0)
    e2 = analysis.energi_joule(6.0)
    assert math.isclose(e2 / e1, 10 ** 1.5, rel_tol=1e-9)


def test_b_value_katalog_sintetis():
    # katalog dengan b ~ 1.0 mengikuti sebaran eksponensial
    mag = [5.2, 5.5, 5.1, 5.3, 5.2, 6.0, 5.4, 5.2, 5.6, 5.1,
           5.3, 5.2, 5.2, 5.9, 5.1, 5.4, 5.2, 5.7, 5.3, 5.2]
    df = pd.DataFrame({"magnitude": mag})
    hasil = analysis.b_value(df)
    assert hasil["tersedia"] is True
    assert hasil["mc"] == 5.3
    assert 0.5 < hasil["b_value"] < 2.5


def test_b_value_data_terlalu_sedikit():
    df = pd.DataFrame({"magnitude": [5.1, 5.2, 5.3]})
    assert analysis.b_value(df)["tersedia"] is False
