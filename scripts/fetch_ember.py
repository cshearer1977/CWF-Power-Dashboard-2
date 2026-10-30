"""
Fetch Ember ANNUAL electricity generation by fuel (TWh) for the target
countries and years, write scripts/_cache/ember.json.

Primary path: Ember API (needs EMBER_API_KEY in .env or the environment)
    GET https://api.ember-energy.org/v1/electricity-generation/yearly

Testing only: `python scripts/fetch_ember.py --bulk-csv` reads Ember's public
bulk CSV (yearly_full_release_long_format.csv) instead of the API, so the
pipeline can be checked without a key. The scheduled workflow always uses the API.

Output shape:
  { fetched_at, method, data: { ISO3: { fuel: { "YYYY": twh } } } }
A missing key means Ember has no value for that country-fuel-year.
"""

from __future__ import annotations

import csv
import io
import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

from config import EMBER_SERIES_MAP, END_YEAR, START_YEAR, TARGET_COUNTRIES

HERE = Path(__file__).parent
REPO = HERE.parent
CACHE_DIR = HERE / "_cache"
CACHE_DIR.mkdir(exist_ok=True)
OUT_PATH = CACHE_DIR / "ember.json"

load_dotenv(REPO / ".env")
API_KEY = os.environ.get("EMBER_API_KEY", "").strip()

API_URL = "https://api.ember-energy.org/v1/electricity-generation/yearly"
BULK_CSV_URL = (
    "https://storage.googleapis.com/emb-prod-bkt-publicdata/"
    "public-downloads/yearly_full_release_long_format.csv"
)


def empty_store() -> dict:
    return {iso3: {} for iso3 in TARGET_COUNTRIES}


def put(store: dict, iso3: str, series: str, year: int, value) -> None:
    fuel = EMBER_SERIES_MAP.get((series or "").strip().lower())
    if fuel is None or iso3 not in store or value is None:
        return
    if not (START_YEAR <= year <= END_YEAR):
        return
    store[iso3].setdefault(fuel, {})[str(year)] = round(float(value), 4)


def fetch_api() -> dict:
    params = {
        "entity_code": ",".join(TARGET_COUNTRIES),
        "is_aggregate_series": "false",
        "start_date": str(START_YEAR),
        "end_date": str(END_YEAR),
        "api_key": API_KEY,
    }
    r = requests.get(API_URL, params=params, timeout=120)
    print(f"  [{r.status_code}] {API_URL}")
    r.raise_for_status()
    payload = r.json()
    rows = payload.get("data", []) if isinstance(payload, dict) else payload

    if not rows:
        sys.exit(f"ERROR: Ember API returned no rows. Response head: {str(payload)[:300]}")
    store = empty_store()
    for row in rows:
        year = int(str(row.get("date"))[:4])
        put(store, row.get("entity_code"), row.get("series"), year, row.get("generation_twh"))
    return store


def fetch_bulk_csv() -> dict:
    r = requests.get(BULK_CSV_URL, timeout=300)
    print(f"  [{r.status_code}] bulk CSV ({len(r.content) / 1e6:.1f} MB)")
    r.raise_for_status()
    store = empty_store()
    for row in csv.DictReader(io.StringIO(r.content.decode("utf-8"))):
        if (row["Category"] != "Electricity generation" or row["Subcategory"] != "Fuel"
                or row["Unit"] != "TWh" or row["Value"] == ""):
            continue
        put(store, row["ISO 3 code"], row["Variable"], int(row["Year"]), row["Value"])
    return store


def main() -> None:
    print(f"Ember annual generation {START_YEAR}-{END_YEAR}, {len(TARGET_COUNTRIES)} countries")
    if "--bulk-csv" in sys.argv:
        print("NOTE: --bulk-csv set - reading Ember's public bulk CSV, not the API.")
        method = "bulk_csv"
        store = fetch_bulk_csv()
    else:
        if not API_KEY:
            sys.exit("ERROR: EMBER_API_KEY not set. Copy .env.example to .env or set the env var.")
        method = "api"
        store = fetch_api()

    print("\nYears with any Ember data, per country:")
    for iso3, fuels in store.items():
        yrs = sorted({y for f in fuels.values() for y in f})
        print(f"  {iso3}: {yrs[0] if yrs else '-'}-{yrs[-1] if yrs else '-'} ({len(yrs)} yrs)")

    if not any(store.values()):
        sys.exit("ERROR: Ember returned no data - leaving previous cache untouched.")

    OUT_PATH.write_text(json.dumps({
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "method": method,
        "data": store,
    }, indent=1))
    print(f"\nWrote {OUT_PATH}")


if __name__ == "__main__":
    main()
