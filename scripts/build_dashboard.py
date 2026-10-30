"""
Merge Ember (primary) and Climate TRACE (gap-fill) annual generation into the
files the dashboard reads:

  docs/data/generation.json   - consumed by docs/index.html
  docs/data/generation.csv    - long-format download (country, fuel, year, TWh, source)

Rule, applied per country x fuel x year:
  Ember value present          -> use Ember
  Ember missing, CT present    -> use Climate TRACE (flagged as "ct")
  both missing                 -> null (shown as a gap)

A year is flagged "partial" when a fuel the country generates from (non-zero
in some year) is missing for that year, so totals and shares for it are understated.
"""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path

from config import FUELS, TARGET_COUNTRIES, YEARS

HERE = Path(__file__).parent
REPO = HERE.parent
CACHE = HERE / "_cache"
OUT_DIR = REPO / "docs" / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load(path: Path) -> dict:
    if not path.exists():
        print(f"WARN: {path.name} missing - treating as empty")
        return {"data": {}}
    return json.loads(path.read_text())


def main() -> None:
    ember = load(CACHE / "ember.json")
    ct = load(CACHE / "climate_trace.json")

    countries = {}
    csv_rows = []
    total_ct = 0

    for iso3, name in TARGET_COUNTRIES.items():
        emb = ember["data"].get(iso3, {})
        trc = ct["data"].get(iso3, {})

        values: dict[str, list] = {}
        sources: dict[str, list] = {}
        ct_cells = []
        for fuel in FUELS:
            vrow, srow = [], []
            for y in YEARS:
                e = emb.get(fuel, {}).get(str(y))
                t = trc.get(fuel, {}).get(str(y))
                if e is not None:
                    v, s = e, "ember"
                elif t is not None:
                    v, s = round(t["twh"], 3), "ct"
                    ct_cells.append({"fuel": fuel, "year": y, "twh": v, "plants": t["plants"]})
                else:
                    v, s = None, None
                vrow.append(v)
                srow.append(s)
                if v is not None:
                    csv_rows.append([name, iso3, fuel, y, v,
                                     "Ember" if s == "ember" else "Climate TRACE"])
            values[fuel] = vrow
            sources[fuel] = srow

        # fuels the country actually generates from (non-zero in some year)
        reported = [f for f in FUELS if any(v for v in values[f])]
        year_status = []
        for i, _ in enumerate(YEARS):
            have = [f for f in reported if values[f][i] is not None]
            missing = [f for f in reported if values[f][i] is None]
            uses_ct = any(sources[f][i] == "ct" for f in FUELS)
            if not have:
                status = "none"
            elif missing:
                status = "partial"
            else:
                status = "complete"
            year_status.append({"status": status, "missing": missing, "uses_ct": uses_ct})

        total_ct += len(ct_cells)
        countries[iso3] = {
            "name": name,
            "values": values,
            "sources": sources,
            "ct_cells": ct_cells,
            "year_status": year_status,
        }
        flagged = [f"{YEARS[i]}({s['status']})" for i, s in enumerate(year_status)
                   if s["status"] != "complete" or s["uses_ct"]]
        print(f"  {iso3} {name:<13} CT cells: {len(ct_cells):>2}  {' '.join(flagged)}")

    payload = {
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ember_fetched_at": ember.get("fetched_at"),
        "ember_method": ember.get("method"),
        "climate_trace_fetched_at": ct.get("fetched_at"),
        "years": YEARS,
        "fuels": FUELS,
        "countries": countries,
    }
    (OUT_DIR / "generation.json").write_text(json.dumps(payload, separators=(",", ":")))

    with open(OUT_DIR / "generation.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["country", "iso3", "fuel", "year", "generation_twh", "source"])
        w.writerows(csv_rows)

    print(f"Wrote generation.json + generation.csv ({total_ct} Climate TRACE cells)")


if __name__ == "__main__":
    main()
