"""
Fetch Climate TRACE ANNUAL plant-level electricity generation and aggregate it
to country x fuel x year (TWh). Used only to fill gaps in Ember.

    GET https://api.climatetrace.org/v7/sources?sectors=power&gadmId=ISO3&year=YYYY

Each plant record carries its annual `activity` in MWh. Plants are assigned to
a fuel by the FIRST fuel in their `assetType` (e.g. "gas, other_fossil" -> Gas).
Climate TRACE models emitting plants only (coal, gas, oil, biomass), and the
v7 asset endpoint currently starts in 2021; earlier years return nothing.

No API key needed. Writes scripts/_cache/climate_trace.json:
  { fetched_at, data: { ISO3: { fuel: { "YYYY": {twh, plants} } } } }
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests

from config import CT_FUEL_MAP, TARGET_COUNTRIES, YEARS

HERE = Path(__file__).parent
CACHE_DIR = HERE / "_cache"
CACHE_DIR.mkdir(exist_ok=True)
OUT_PATH = CACHE_DIR / "climate_trace.json"

BASE_URL = "https://api.climatetrace.org/v7/sources"
PAGE = 100
DELAY = 0.2


def get_power_sources(iso3: str, year: int) -> list[dict]:
    out: list[dict] = []
    offset = 0
    while True:
        page = None
        for attempt in range(4):  # the API throws occasional 502s
            try:
                r = requests.get(BASE_URL, params={
                    "sectors": "power", "gadmId": iso3, "year": year,
                    "limit": PAGE, "offset": offset,
                }, timeout=60)
                r.raise_for_status()
                page = r.json() or []
                break
            except Exception as e:  # noqa: BLE001
                if attempt == 3:
                    print(f"  [ERROR] {iso3} {year} offset={offset}: {e}", file=sys.stderr)
                time.sleep(2 * (attempt + 1))
        if page is None:
            break
        out.extend(page)
        if len(page) < PAGE:
            break
        offset += PAGE
        time.sleep(DELAY)
    return out


def primary_fuel(asset_type: str | None) -> str | None:
    first = (asset_type or "").split(",")[0].strip().lower()
    return CT_FUEL_MAP.get(first)


def main() -> None:
    print(f"Climate TRACE annual plant activity, years {YEARS[0]}-{YEARS[-1]}")
    data: dict = {iso3: {} for iso3 in TARGET_COUNTRIES}

    for iso3, name in TARGET_COUNTRIES.items():
        summary = []
        for year in YEARS:
            sources = get_power_sources(iso3, year)
            time.sleep(DELAY)
            if not sources:
                continue
            for s in sources:
                if s.get("subsector") != "electricity-generation":
                    continue
                if (s.get("activityUnits") or "MWh") != "MWh":
                    continue
                fuel = primary_fuel(s.get("assetType"))
                act = s.get("activity")
                if fuel is None or act is None:
                    continue
                cell = data[iso3].setdefault(fuel, {}).setdefault(str(year), {"twh": 0.0, "plants": 0})
                cell["twh"] += act / 1e6
                cell["plants"] += 1
            summary.append(f"{year}:{len(sources)}")
        print(f"  {iso3} {name:<13} plants/yr  " + " ".join(summary))

    for fuels in data.values():
        for years in fuels.values():
            for cell in years.values():
                cell["twh"] = round(cell["twh"], 4)

    if not any(data.values()):
        sys.exit("ERROR: Climate TRACE returned no data - leaving previous cache untouched.")

    OUT_PATH.write_text(json.dumps({
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "data": data,
    }, indent=1))
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
