# Annual Generation Dashboard — 15 Countries

Static dashboard of annual electricity generation by fuel (TWh), 2016–2025, for
Indonesia, Pakistan, Philippines, Thailand, Vietnam, Brazil, Colombia, Mexico,
Ethiopia, Ghana, Kenya, Nigeria, Senegal, South Africa and Tanzania.

Fuels (same rows as the CWF underlying-data spreadsheet): Solar, Wind, Hydro,
Bioenergy, Other renewables, Nuclear, Gas, Coal, Other fossil.

## Data sources

| Step | Source | Notes |
|---|---|---|
| Primary | Ember API, `/v1/electricity-generation/yearly` | needs `EMBER_API_KEY` |
| Gap-fill | Climate TRACE API v7, `/sources?sectors=power` | no key; plant-level annual activity (MWh) summed by country × primary fuel |

Rule, per country × fuel × year: use Ember; if Ember has no value, use Climate
TRACE; otherwise leave blank. Climate TRACE values are hatched in the chart,
shown in **blue** in the table, and listed (with plant counts) under the table.

Limits of the Climate TRACE fill:
- Covers emitting plants only (coal, gas, oil, biomass) — it cannot fill solar,
  wind, hydro, nuclear or other renewables.
- Plant-level asset data starts in 2021.
- Coverage of small/captive plants can be incomplete, so filled values may
  understate generation.

A year where a fuel the country normally generates from is missing is marked
`*` (incomplete) and the dashboard says which fuels are missing.

## Layout

```
├── .env.example                  # copy to .env; holds EMBER_API_KEY
├── requirements.txt
├── scripts/
│   ├── config.py                 # countries, years, fuel list and mappings
│   ├── fetch_ember.py            # -> scripts/_cache/ember.json
│   ├── fetch_climate_trace.py    # -> scripts/_cache/climate_trace.json
│   └── build_dashboard.py        # -> docs/data/generation.json + .csv
├── docs/                         # served by GitHub Pages
│   ├── index.html
│   └── data/
└── .github/workflows/update-data.yml   # daily 06:45 UTC + manual run
```

## Local run

```bash
cp .env.example .env            # then set EMBER_API_KEY
pip install -r requirements.txt
python scripts/fetch_ember.py
python scripts/fetch_climate_trace.py
python scripts/build_dashboard.py
python -m http.server --directory docs 8000   # open http://localhost:8000
```

`python scripts/fetch_ember.py --bulk-csv` reads Ember's public bulk CSV instead
of the API (same dataset) for testing without a key. The workflow always uses
the API.

## GitHub setup

1. Push this folder to a new GitHub repo.
2. **Settings → Secrets and variables → Actions**: add secret `EMBER_API_KEY`.
3. **Settings → Pages**: Source = **GitHub Actions**.
4. **Actions → Daily data refresh → Run workflow** for the first build.

## Changing scope

Edit `scripts/config.py` (`TARGET_COUNTRIES`, `START_YEAR`, `END_YEAR`).
