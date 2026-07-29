"""
Zillow Research ZHVI (Zillow Home Value Index) market data.
Zillow publishes public CSV files of median home values by ZIP code —
no auth, no API key, no scraping protection.
This gives a live, accurate area median for the NWA market.
"""
import csv
import io
import logging
import statistics

import requests

from config import AREA, BROWSER_HEADERS

log = logging.getLogger(__name__)

# Zillow Research public CSV - Single-Family / Condo tier, smoothed seasonally adjusted
# Updated monthly. ~30 MB national file — we stream and filter inline.
_ZHVI_URL = (
    "https://files.zillowstatic.com/research/public_csvs/zhvi/"
    "Zip_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
)

# Typical NWA sqft median — used to convert home value → $/sqft
# Bentonville/Rogers area homes typically run 1,800–2,400 sqft
_MEDIAN_SQFT_ESTIMATE = 2_100


def _stream_zhvi() -> dict[str, float]:
    """
    Stream the ZHVI CSV, filter to NWA ZIP codes, return {zip: latest_value}.
    We read only the header + matching rows to avoid loading 30 MB into RAM.
    """
    target_zips = set(AREA["zip_codes"])
    results: dict[str, float] = {}

    log.info("Zillow Research: streaming ZHVI CSV...")
    try:
        resp = requests.get(
            _ZHVI_URL,
            headers={**BROWSER_HEADERS, "Accept-Encoding": "gzip, deflate"},
            stream=True,
            timeout=30,
        )
        resp.raise_for_status()
    except Exception as exc:
        log.warning("Zillow Research CSV fetch failed: %s", exc)
        return {}

    # Parse streaming, line by line
    header: list[str] = []
    for raw_bytes in resp.iter_lines():
        if not raw_bytes:
            continue
        raw_line = raw_bytes.decode("utf-8", errors="replace") if isinstance(raw_bytes, bytes) else raw_bytes
        row = next(csv.reader([raw_line]))
        if not header:
            header = row
            continue
        if len(row) < 5:
            continue
        # Column 2 is 'RegionName' (ZIP code)
        zip_code = row[2].strip().zfill(5) if len(row) > 2 else ""
        if zip_code not in target_zips:
            continue
        # Last non-empty column = most recent month value
        recent_val = None
        for val in reversed(row):
            if val.strip():
                try:
                    recent_val = float(val)
                    break
                except ValueError:
                    pass
        if recent_val:
            results[zip_code] = recent_val
        if len(results) >= len(target_zips):
            break   # got all we need — stop streaming

    resp.close()
    log.info(
        "Zillow ZHVI: found %d/%d NWA ZIPs: %s",
        len(results), len(target_zips),
        {z: f"${v:,.0f}" for z, v in results.items()},
    )
    return results


def get_area_median_price_per_sqft() -> float | None:
    """
    Return estimated area median $/sqft from Zillow ZHVI.
    Divides median home value by the typical NWA median sqft.
    Returns None if the CSV is unreachable.
    """
    zhvi = _stream_zhvi()
    if not zhvi:
        return None
    median_value = statistics.median(zhvi.values())
    ppqft = round(median_value / _MEDIAN_SQFT_ESTIMATE, 2)
    log.info(
        "Zillow market data: area median home value $%.0f → $%.0f/sqft "
        "(assuming %d sqft median size)",
        median_value, ppqft, _MEDIAN_SQFT_ESTIMATE,
    )
    return ppqft
