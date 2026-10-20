"""Penyusunan laporan markdown dari hasil analisis."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

MARKER_MULAI = "<!-- RINGKASAN:START -->"
MARKER_SELESAI = "<!-- RINGKASAN:END -->"


def fmt(v: float | int | None, desimal: int = 1) -> str:
    """Format angka gaya Indonesia: 1.234,5"""
    if v is None:
        return "-"
    teks = f"{float(v):,.{desimal}f}"
    return teks.replace(",", "@").replace(".", ",").replace("@", ".")


def _tabel(header: list[str], rows: list[list[str]]) -> str:
    if not rows:
        rows = [["-"] * len(header)]
    garis = "| " + " | ".join(header) + " |"
    pisah = "|" + "|".join(["---"] * len(header)) + "|"
    isi = ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join([garis, pisah, *isi])


def blok_ringkasan(ringkas: dict[str, Any], b: dict, energi: dict, waktu_ambil: str) -> str:
    mag = ringkas["magnitudo"]
    ked = ringkas["kedalaman"]
    baris = [
        f"**Data diambil:** {waktu_ambil}  ",
        f"**Gempa dalam katalog:** {ringkas['jumlah']} kejadian "
        f"({ringkas['jumlah_katalog_m5']} dari katalog M5+, {ringkas['jumlah_dirasakan']} dirasakan)  ",
        f"**Magnitudo:** rata-rata {fmt(mag['rata_rata'], 2)}, terbesar M{fmt(mag['maks'], 1)}  ",
        f"**Kedalaman median:** {fmt(ked['median'])} km "
        f"({fmt(ringkas['porsi_dangkal_persen'])}% gempa dangkal)  ",
    ]
    if b.get("tersedia"):
        catatan = "" if b["stabil"] else " (indikatif, sampel kecil)"
        baris.append(f"**b-value Gutenberg-Richter:** {fmt(b['b_value'], 2)} "
                     f"+- {fmt(b['standar_error'], 2)}{catatan}  ")
    if energi:
        baris.append(f"**Total energi seismik:** {fmt(energi['total_joule'] / 1e15, 2)} PJ "
                     f"(setara {fmt(energi['total_ton_tnt'], 0)} ton TNT)  ")
    baris.append(f"**Berpotensi tsunami:** {ringkas['gempa_berpotensi_tsunami']} kejadian")
    return "\n".join(baris)


def buat_laporan(
    df: pd.DataFrame,
    ringkas: dict[str, Any],
    b: dict[str, Any],
    energi: dict[str, Any],
    jeda: dict[str, Any],
    korelasi: float | None,
    gambar: list[Path],
    waktu_ambil: str,
) -> str:
    terbesar = ringkas["gempa_terbesar"]
    mag = ringkas["magnitudo"]
    ked = ringkas["kedalaman"]

    baris_gempa = [
        [
            row["waktu_utc"].strftime("%d/%m %H:%M"),
            f"M{fmt(row['magnitude'], 1)}",
            fmt(row["kedalaman_km"], 0),
            row["provinsi"],
            row["wilayah"][:64],
        ]
        for _, row in df.sort_values("magnitude", ascending=False).head(12).iterrows()
    ]
    baris_prov = [[p, str(n)] for p, n in ringkas["provinsi_terbanyak"].items()]
    baris_mag = [[m, str(n)] for m, n in ringkas["sebaran_magnitudo"].items()]
    baris_ked = [[k, str(v)] for k, v in ringkas["sebaran_kedalaman"].items()]

    insight: list[str] = []
    insight.append(
        f"Gempa terbesar M{fmt(terbesar['magnitude'], 1)} di {terbesar['wilayah']} "
        f"({terbesar['provinsi']}), kedalaman {fmt(terbesar['kedalaman_km'], 0)} km."
    )
    if ringkas["porsi_dangkal_persen"] >= 50:
        insight.append(
            f"{fmt(ringkas['porsi_dangkal_persen'])}% gempa di katalog ini dangkal (<70 km). "
            "Gempa dangkal terasa lebih kuat di permukaan pada magnitudo yang sama."
        )
    else:
        insight.append(
            f"Sebagian besar gempa berada di kedalaman menengah sampai dalam "
            f"({fmt(100 - ringkas['porsi_dangkal_persen'])}%), jejak lempeng yang menunjam."
        )
    if energi:
        insight.append(
            f"Satu gempa terbesar menyumbang {fmt(energi['pangsa_gempa_terbesar_persen'])}% "
            f"dari total energi lepas ({fmt(energi['total_joule'] / 1e15, 2)} PJ). "
            "Energi seismik didominasi sedikit kejadian besar, bukan banyaknya gempa kecil."
        )
    if b.get("tersedia"):
        if b["stabil"]:
            insight.append(
                f"b-value {fmt(b['b_value'], 2)} +- {fmt(b['standar_error'], 2)} dari "
                f"{b['n_dipakai']} gempa di atas Mc {fmt(b['mc'], 1)}."
            )
        else:
            insight.append(
                f"b-value {fmt(b['b_value'], 2)} +- {fmt(b['standar_error'], 2)} hanya "
                f"dihitung dari {b['n_dipakai']} gempa. Dengan galat baku sebesar itu, "
                "angka ini belum layak dipakai untuk klaim tingkat seismisitas."
            )
    if korelasi is not None:
        arah = "tidak jelas" if abs(korelasi) < 0.2 else ("negatif" if korelasi < 0 else "positif")
        insight.append(
            f"Korelasi kedalaman dan magnitudo {fmt(korelasi, 2)} ({arah}). "
            "Pada katalog sesingkat ini, magnitudo praktis tidak bisa ditebak dari kedalaman."
        )
    if ringkas["gempa_berpotensi_tsunami"]:
        insight.append(
            f"{ringkas['gempa_berpotensi_tsunami']} gempa ditandai berpotensi tsunami. "
            "Untuk keputusan apa pun, ikuti peringatan resmi BMKG."
        )
    else:
        insight.append("Tidak ada gempa yang ditandai berpotensi tsunami di katalog ini.")

    bagian_gambar = "\n\n".join(
        f"![{p.stem}]({p.name})\n\n*{p.stem.replace('_', ' ')}*" for p in gambar
    )

    return f"""# Laporan Gempa Indonesia

Data terbuka BMKG, diambil {waktu_ambil}. Semua angka di bawah dihasilkan pipeline,
tidak ada nilai yang ditulis manual.

{blok_ringkasan(ringkas, b, energi, waktu_ambil)}

## Rentang data

| Metrik | Nilai |
|---|---|
| Periode awal | {ringkas['periode_mulai_utc']} |
| Periode akhir | {ringkas['periode_akhir_utc']} |
| Magnitudo rata-rata | {fmt(mag['rata_rata'], 2)} |
| Magnitudo median | {fmt(mag['median'], 2)} |
| Kedalaman median | {fmt(ked['median'])} km |
| Kedalaman maksimum | {fmt(ked['maks'], 0)} km |
| Provinsi tidak terdeteksi | {ringkas['tanpa_provinsi']} gempa |

## Gempa terbesar

{_tabel(["Waktu (UTC)", "Magnitudo", "Kedalaman (km)", "Provinsi", "Wilayah BMKG"], baris_gempa)}

## Provinsi dengan gempa terbanyak

{_tabel(["Provinsi", "Jumlah"], baris_prov)}

## Sebaran magnitudo

{_tabel(["Magnitudo", "Jumlah"], baris_mag)}

## Sebaran kedalaman

{_tabel(["Kategori", "Jumlah"], baris_ked)}

## Jeda antar gempa

{_tabel(
    ["Metrik", "Nilai"],
    [["Median", f"{fmt(jeda.get('jeda_median_jam'))} jam"],
     ["Rata-rata", f"{fmt(jeda.get('jeda_rata_rata_jam'))} jam"],
     ["Terpendek", f"{fmt(jeda.get('jeda_terpendek_jam'))} jam"],
     ["Terpanjang", f"{fmt(jeda.get('jeda_terpanjang_jam'))} jam"]] if jeda else [],
)}

## Catatan analisis

""" + "\n".join(f"- {i}" for i in insight) + f"""

## Gambar

{bagian_gambar}

## Keterbatasan

- Katalog publik BMKG hanya memuat gempa M5,0 ke atas dan gempa yang dirasakan, bukan
  katalog lengkap. Semua statistik mewarisi batas itu, termasuk b-value.
- Provinsi ditebak dari teks bebas BMKG. Kalau formatnya tidak lazim, gempa masuk kategori
  "Tidak diketahui" dan tetap bisa diperiksa lewat kolom `wilayah`.
- Data diambil sekali per eksekusi. Untuk kejadian terkini, sumber resminya tetap BMKG.
"""


def tulis_laporan(teks: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(teks, encoding="utf-8")
    return path


def tulis_json(data: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return path


def perbarui_readme(readme: Path, blok: str) -> None:
    """Ganti isi blok ringkasan di README supaya angka selalu segar."""
    if not readme.exists():
        return
    teks = readme.read_text(encoding="utf-8")
    if MARKER_MULAI not in teks or MARKER_SELESAI not in teks:
        return
    awal = teks.index(MARKER_MULAI) + len(MARKER_MULAI)
    akhir = teks.index(MARKER_SELESAI)
    baru = teks[:awal] + "\n" + blok + "\n" + teks[akhir:]
    readme.write_text(baru, encoding="utf-8")


def waktu_sekarang() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
