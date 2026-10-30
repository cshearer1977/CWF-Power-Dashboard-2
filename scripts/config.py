"""Shared settings for the annual generation dashboard."""

TARGET_COUNTRIES: dict[str, str] = {
    "IDN": "Indonesia",
    "PAK": "Pakistan",
    "PHL": "Philippines",
    "THA": "Thailand",
    "VNM": "Vietnam",
    "BRA": "Brazil",
    "COL": "Colombia",
    "MEX": "Mexico",
    "ETH": "Ethiopia",
    "GHA": "Ghana",
    "KEN": "Kenya",
    "NGA": "Nigeria",
    "SEN": "Senegal",
    "ZAF": "South Africa",
    "TZA": "Tanzania",
}

START_YEAR = 2016
END_YEAR = 2025
YEARS = list(range(START_YEAR, END_YEAR + 1))

# Row order matches the CWF underlying-data spreadsheet.
FUELS = [
    "Solar",
    "Wind",
    "Hydro",
    "Bioenergy",
    "Other renewables",
    "Nuclear",
    "Gas",
    "Coal",
    "Other fossil",
]

# Ember series name (lower-cased; the API and bulk CSV differ in capitalisation)
# -> dashboard fuel name
EMBER_SERIES_MAP = {
    "solar": "Solar",
    "wind": "Wind",
    "hydro": "Hydro",
    "bioenergy": "Bioenergy",
    "other renewables": "Other renewables",
    "nuclear": "Nuclear",
    "gas": "Gas",
    "coal": "Coal",
    "other fossil": "Other fossil",
}

# Climate TRACE plant assetType (primary fuel = first listed) -> dashboard fuel.
# Climate TRACE covers emitting plants only, so hydro, solar, wind, nuclear and
# "other renewables" can never be filled from it.
CT_FUEL_MAP = {
    "coal": "Coal",
    "gas": "Gas",
    "oil": "Other fossil",
    "other_fossil": "Other fossil",
    "biomass": "Bioenergy",
}
