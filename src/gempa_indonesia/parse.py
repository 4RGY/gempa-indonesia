"""Parser field BMKG yang formatnya masih berupa teks bebas berbahasa Indonesia."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

_ANGKA = re.compile(r"-?\d+(?:[.,]\d+)?")


def _to_float(text: str | float | int) -> float:
    """Ambil angka pertama dari teks. Dukung '5.4', '5,4', '1.234,5', dan '74 km'."""
    if isinstance(text, (int, float)):
        return float(text)
    bersih = str(text).strip()
    if "." in bersih and "," in bersih:      # format Indonesia: 1.234,5
        bersih = bersih.replace(".", "").replace(",", ".")
    elif "," in bersih:                       # 5,4
        bersih = bersih.replace(",", ".")
    match = _ANGKA.search(bersih)
    if not match:
        raise ValueError(f"angka tidak ditemukan pada: {text!r}")
    return float(match.group(0))


def parse_magnitude(text: str | float) -> float:
    """'5.4' -> 5.4"""
    return _to_float(text)


def parse_depth_km(text: str | float) -> float:
    """'74 km' -> 74.0 ; '10 km' -> 10.0"""
    return _to_float(str(text).lower().replace("km", "").strip())


def parse_lintang(text: str) -> float:
    """'3.79 LU' -> 3.79 ; '8.09 LS' -> -8.09"""
    nilai = _to_float(text)
    huruf = str(text).upper()
    if "LS" in huruf:
        return -abs(nilai)
    if "LU" in huruf:
        return abs(nilai)
    raise ValueError(f"arah lintang tidak dikenali: {text!r}")


def parse_bujur(text: str) -> float:
    """'95.72 BT' -> 95.72 ; '110.10 BB' -> -110.10"""
    nilai = _to_float(text)
    huruf = str(text).upper()
    if "BB" in huruf:
        return -abs(nilai)
    if "BT" in huruf:
        return abs(nilai)
    raise ValueError(f"arah bujur tidak dikenali: {text!r}")


def parse_datetime_utc(text: str) -> datetime:
    """'2026-10-20T16:29:35+00:00' -> datetime UTC tz-aware."""
    dt = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_tsunami(potensi: str | None) -> bool:
    """'Tidak berpotensi tsunami' -> False ; 'Berpotensi tsunami' -> True."""
    if not potensi:
        return False
    return "tidak" not in str(potensi).lower()


def normalize(record: dict[str, Any], sumber: str) -> dict[str, Any]:
    """Ubah satu record mentah BMKG jadi baris tabular yang siap dianalisis."""
    return {
        "sumber": sumber,
        "waktu_utc": parse_datetime_utc(record["DateTime"]),
        "tanggal": record.get("Tanggal"),
        "jam_wib": record.get("Jam"),
        "lintang": parse_lintang(record["Lintang"]),
        "bujur": parse_bujur(record["Bujur"]),
        "magnitude": parse_magnitude(record["Magnitude"]),
        "kedalaman_km": parse_depth_km(record["Kedalaman"]),
        "wilayah": (record.get("Wilayah") or "").strip(),
        "potensi_tsunami": parse_tsunami(record.get("Potensi")),
        "dirasakan": (record.get("Dirasakan") or "").strip() or None,
    }
