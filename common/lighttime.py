"""One-way light time from Earth to Mars, from NASA JPL Horizons (quantity 21)."""
from datetime import datetime, timedelta, timezone

import requests

HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"
# Read from Horizons on 2026-11-13: Mars seen from Earth's centre, in seconds.
FALLBACK_S = {"2026-11-14": 660.86, "2026-11-15": 656.62, "2026-11-16": 652.36}
FALLBACK_NOTE = "JPL Horizons, read on 2026-11-13"
_cache = {}

C_KM_S = 299_792.458        # speed of light in km/s, exact by definition
AU_KM = 149_597_870.7       # one astronomical unit in km (IAU 2012)


def path_km(delay_s):
    """How far a signal travels in delay_s seconds."""
    return delay_s * C_KM_S


def parse(text):
    """Return seconds from a Horizons CSV ephemeris that holds quantity 21."""
    first_row = text.split("$$SOE")[1].split("$$EOE")[0].strip().splitlines()[0]
    numbers = []
    for field in first_row.split(","):
        try:
            numbers.append(float(field))
        except ValueError:
            pass
    return numbers[-1] * 60.0


def fetch(day):
    next_day = (datetime.strptime(day, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    params = {
        "format": "text", "COMMAND": "'499'", "OBJ_DATA": "'NO'", "MAKE_EPHEM": "'YES'",
        "EPHEM_TYPE": "'OBSERVER'", "CENTER": "'500@399'", "START_TIME": f"'{day}'",
        "STOP_TIME": f"'{next_day}'", "STEP_SIZE": "'1d'", "QUANTITIES": "'21'",
        "CSV_FORMAT": "'YES'",
    }
    response = requests.get(HORIZONS_URL, params=params, timeout=5)
    response.raise_for_status()
    return parse(response.text)


def _lookup(day):
    day = day or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if day not in _cache:
        try:
            _cache[day] = (fetch(day), "JPL Horizons, live")
        except (requests.RequestException, IndexError, ValueError):
            _cache[day] = (FALLBACK_S.get(day, FALLBACK_S["2026-11-15"]), FALLBACK_NOTE)
    return _cache[day]


def mars_seconds(day=None):
    return _lookup(day)[0]


def source(day=None):
    return _lookup(day)[1]
