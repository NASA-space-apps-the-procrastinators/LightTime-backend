"""Cabin air and radiation, replayed from NASA's records of the ISS (Rodent Research 1, 2014)."""
import csv
import functools
import os
import time

CLEAN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "clean")
STEP_S = 5    # one five-minute row plays every five seconds: the same 60 times speed-up as the link
STARTED = time.monotonic()
SOURCE = {"source": "NASA OSDR Environmental Data App, Rodent Research 1 (2014), replayed",
          "url": "https://visualization.osdr.nasa.gov/eda/", "kind": "file"}


@functools.lru_cache(maxsize=None)
def _table(name):
    with open(os.path.join(CLEAN, name), newline="") as f:
        return list(csv.DictReader(f))


def at(elapsed_s):
    """The cabin row and that day's radiation dose, `elapsed_s` seconds after the server started."""
    cabin = _table("cabin_rr1.csv")
    row = cabin[int(elapsed_s // STEP_S) % len(cabin)]
    dose = next((r for r in _table("radiation_rr1.csv") if r["date"] == row["time"][:10]), None)
    return {
        "cabin": {"temp_c": float(row["temp_c"]), "humidity_pct": float(row["humidity_pct"]),
                  "co2_ppm": float(row["co2_ppm"]), "as_of": row["time"]},
        "radiation": {"total_mgy_day": float(dose["total_mgy_day"]), "gcr_mgy_day": float(dose["gcr_mgy_day"]),
                      "saa_mgy_day": float(dose["saa_mgy_day"]), "as_of": dose["date"]} if dose else None,
        **SOURCE,
    }
