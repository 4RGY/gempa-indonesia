"""Ambil katalog gempa terkini dari API terbuka BMKG."""

from __future__ import annotations

import json
import time
from typing import Any

import requests

BASE_URL = "https://data.bmkg.go.id/DataMKG/TEWS"
ENDPOINTS = {
    "gempaterkini": f"{BASE_URL}/gempaterkini.json",      # gempa M >= 5.0 terbaru
    "gempadirasakan": f"{BASE_URL}/gempadirasakan.json",  # gempa yang dirasakan
}
HEADERS = {"User-Agent": "gempa-indonesia/1.0 (data analyst portfolio; BMKG open data)"}


def fetch_json(url: str, timeout: int = 30, retries: int = 3) -> dict[str, Any]:
    """GET JSON dengan retry sederhana dan backoff eksponensial."""
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001 - jaringan publik, apa pun bisa terjadi
            last_error = exc
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"gagal mengambil {url}: {last_error}")


def fetch_raw_catalog() -> dict[str, list[dict[str, Any]]]:
    """Kembalikan katalog mentah per sumber, tanpa transformasi apa pun."""
    raw: dict[str, list[dict[str, Any]]] = {}
    for nama, url in ENDPOINTS.items():
        payload = fetch_json(url)
        raw[nama] = payload.get("Infogempa", {}).get("gempa", [])
    return raw
