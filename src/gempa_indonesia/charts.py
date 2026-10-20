"""Visualisasi katalog gempa. Gaya: bersih, terang, tanpa dekorasi berlebih."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

TINTA = "#1c2430"
ABU = "#6b7a8f"
GARIS = "#dfe5ec"
AKSEN = "#0f766e"
AMBER = "#d97706"
MERAH = "#b3261e"
BIRU = "#1d4ed8"

WARNA_KEDALAMAN = {"dangkal": AMBER, "menengah": AKSEN, "dalam": BIRU}


def _gaya() -> None:
    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": GARIS,
        "axes.labelcolor": TINTA,
        "axes.titlecolor": TINTA,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.labelsize": 10,
        "axes.grid": True,
        "grid.color": GARIS,
        "grid.linewidth": 0.7,
        "xtick.color": ABU,
        "ytick.color": ABU,
        "font.size": 9.5,
        "figure.dpi": 150,
        "savefig.bbox": "tight",
    })
    for spine in ("top", "right"):
        plt.rcParams[f"axes.spines.{spine}"] = False


def _simpan(fig: plt.Figure, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    return path


def _ukuran(mag: pd.Series, dasar: float = 22.0, pengali: float = 55.0) -> pd.Series:
    """Ukuran marker proporsional magnitudo, tidak pernah negatif."""
    return (dasar + (mag - mag.min()) * pengali).clip(lower=14.0)


def timeline_magnitudo(df: pd.DataFrame, path: Path) -> Path:
    _gaya()
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    for kategori, grup in df.groupby("kategori_kedalaman"):
        ax.scatter(
            grup["waktu_utc"], grup["magnitude"],
            s=_ukuran(grup["magnitude"]),
            color=WARNA_KEDALAMAN.get(kategori, ABU),
            alpha=0.8, edgecolor="white", linewidth=0.7, label=f"{kategori}",
        )
    ax.set_title("Magnitudo gempa M5+ yang tercatat BMKG")
    ax.set_ylabel("Magnitudo")
    ax.set_xlabel("Waktu (UTC)")
    ax.legend(title="Kedalaman", frameon=False, loc="upper left", fontsize=8.5)
    ax.set_ylim(df["magnitude"].min() - 0.4, df["magnitude"].max() + 0.4)
    fig.autofmt_xdate(rotation=0, ha="center")
    return _simpan(fig, path)


def kedalaman_vs_magnitudo(df: pd.DataFrame, path: Path) -> Path:
    _gaya()
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    warna = df["kategori_kedalaman"].map(WARNA_KEDALAMAN).fillna(ABU)
    ax.axhspan(0, 70, color=AMBER, alpha=0.06)
    ax.scatter(df["kedalaman_km"], df["magnitude"], s=42, c=warna, alpha=0.85,
               edgecolor="white", linewidth=0.8)
    ax.text(ax.get_xlim()[1] * 0.99, 62, "zona dangkal (<70 km)",
            ha="right", va="top", fontsize=8.5, color=AMBER)
    ax.set_title("Kedalaman vs magnitudo")
    ax.set_xlabel("Kedalaman (km)")
    ax.set_ylabel("Magnitudo")
    return _simpan(fig, path)


def distribusi_gutenberg_richter(df: pd.DataFrame, b: dict, path: Path) -> Path:
    _gaya()
    fig, ax = plt.subplots(figsize=(8.0, 4.6))
    mag = df["magnitude"].round(1)
    ax.hist(mag, bins=np.arange(4.9, mag.max() + 0.25, 0.2), color=AKSEN,
            alpha=0.85, edgecolor="white", linewidth=0.8, label="jumlah gempa")
    ax.set_xlabel("Magnitudo")
    ax.set_ylabel("Jumlah gempa", color=TINTA)
    ax.set_title("Sebaran magnitudo dan hukum Gutenberg-Richter")

    ax2 = ax.twinx()
    ax2.grid(False)
    nilai = np.sort(mag.to_numpy())
    kumulatif = np.array([(nilai >= m).sum() for m in nilai])
    ax2.semilogy(nilai, kumulatif, "o", color=MERAH, markersize=4.5,
                 label="N(>=M) kumulatif")
    if b.get("tersedia"):
        x = np.linspace(5.0, nilai.max(), 50)
        n0 = max(kumulatif[0], 1)
        ax2.semilogy(x, n0 * 10 ** (-b["b_value"] * (x - 5.0)), "--", color=MERAH,
                     linewidth=1.4, label=f"fit b = {b['b_value']:.2f}")
    ax2.set_ylabel("N(>=M) kumulatif (log)", color=MERAH)
    ax2.tick_params(axis="y", colors=MERAH)
    for spine in ("top",):
        ax2.spines[spine].set_visible(False)

    garis1, label1 = ax.get_legend_handles_labels()
    garis2, label2 = ax2.get_legend_handles_labels()
    ax.legend(garis1 + garis2, label1 + label2, frameon=False, fontsize=8.5, loc="upper right")
    return _simpan(fig, path)


def peta_episentrum(df: pd.DataFrame, path: Path) -> Path:
    _gaya()
    fig, ax = plt.subplots(figsize=(10.0, 4.8))
    skala = _ukuran(df["magnitude"], dasar=28.0, pengali=90.0)
    warna = df["kategori_kedalaman"].map(WARNA_KEDALAMAN).fillna(ABU)
    ax.scatter(df["bujur"], df["lintang"], s=skala, c=warna, alpha=0.75,
               edgecolor="white", linewidth=0.8)
    for _, row in df.nlargest(3, "magnitude").iterrows():
        ax.annotate(f"M{row['magnitude']:.1f}", (row["bujur"], row["lintang"]),
                    textcoords="offset points", xytext=(7, 5), fontsize=8,
                    color=TINTA, fontweight="bold")
    ax.set_xlim(93, 142)
    ax.set_ylim(-12, 8)
    ax.set_xlabel("Bujur (BT)")
    ax.set_ylabel("Lintang (LU/LS)")
    ax.set_title("Peta episentrum (batas kasar wilayah Indonesia)")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}"))
    ax.grid(color=GARIS, linewidth=0.6, linestyle=":")
    return _simpan(fig, path)


def buat_semua(df: pd.DataFrame, b: dict, outdir: Path) -> list[Path]:
    return [
        timeline_magnitudo(df, outdir / "01_timeline_magnitudo.png"),
        kedalaman_vs_magnitudo(df, outdir / "02_kedalaman_vs_magnitudo.png"),
        distribusi_gutenberg_richter(df, b, outdir / "03_distribusi_magnitudo.png"),
        peta_episentrum(df, outdir / "04_peta_episentrum.png"),
    ]
