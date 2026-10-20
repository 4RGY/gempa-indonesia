"""CLI: satu perintah untuk ambil data, analisis, gambar, dan laporan."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import analysis, charts, fetch, report


def jalankan(outdir: Path, dengan_gambar: bool = True, readme: Path | None = None) -> dict:
    print("[1/4] ambil katalog BMKG ...")
    raw = fetch.fetch_raw_catalog()
    jumlah_mentah = sum(len(v) for v in raw.values())
    print(f"      {jumlah_mentah} record mentah dari {len(raw)} endpoint")

    df = analysis.build_dataframe(raw)
    if df.empty:
        raise SystemExit("katalog kosong, tidak ada yang bisa dianalisis")
    print(f"      {len(df)} gempa unik setelah deduplikasi")

    print("[2/4] hitung statistik ...")
    ringkas = analysis.ringkasan(df)
    katalog_m5 = df[df["sumber"] == "gempaterkini"]
    b = analysis.b_value(katalog_m5)
    energi = analysis.neraca_energi(df)
    jeda = analysis.statistik_jeda(df)
    korelasi = analysis.korelasi_kedalaman_magnitudo(df)

    outdir.mkdir(parents=True, exist_ok=True)
    df_out = df.copy()
    df_out["waktu_utc"] = df_out["waktu_utc"].dt.strftime("%Y-%m-%dT%H:%M:%S%z")
    df_out.to_csv(outdir / "gempa_bersih.csv", index=False, encoding="utf-8")

    print("[3/4] gambar ...")
    gambar: list[Path] = []
    if dengan_gambar:
        gambar = charts.buat_semua(df, b, outdir)
        for g in gambar:
            print(f"      {g.relative_to(outdir.parent)}")

    print("[4/4] tulis laporan ...")
    waktu = report.waktu_sekarang()
    teks = report.buat_laporan(df, ringkas, b, energi, jeda, korelasi, gambar, waktu)
    report.tulis_laporan(teks, outdir / "laporan.md")
    report.tulis_json(
        {"diambil_pada": waktu, "ringkasan": ringkas, "b_value": b,
         "energi": energi, "jeda": jeda, "korelasi_kedalaman_magnitudo": korelasi},
        outdir / "ringkasan.json",
    )
    if readme:
        report.perbarui_readme(readme, report.blok_ringkasan(ringkas, b, energi, waktu))

    print("\n== ringkas ==")
    print(f"gempa      : {ringkas['jumlah']}")
    print(f"terbesar   : M{ringkas['magnitudo_maks']} {ringkas['gempa_terbesar']['wilayah']}")
    if b.get("tersedia"):
        print(f"b-value    : {b['b_value']} +- {b['standar_error']}")
    print(f"tsunami    : {ringkas['gempa_berpotensi_tsunami']} kejadian ditandai")
    return {"ringkasan": ringkas, "b_value": b, "energi": energi}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analisis katalog gempa BMKG")
    parser.add_argument("--outdir", default="outputs", help="folder output (default: outputs)")
    parser.add_argument("--no-charts", action="store_true", help="lewati pembuatan gambar")
    parser.add_argument("--readme", default="README.md", help="README yang blok ringkasannya diperbarui")
    args = parser.parse_args(argv)

    readme = Path(args.readme)
    jalankan(Path(args.outdir), dengan_gambar=not args.no_charts,
             readme=readme if readme.exists() else None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
