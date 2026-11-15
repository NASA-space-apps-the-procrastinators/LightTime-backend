"""NASA's Deep Space Network Now feed: which antennas are on Mars right now, and the
round-trip light time NASA reports for its spacecraft there. A second check on Horizons."""
import math
import time
import xml.etree.ElementTree as ET

import requests

DSN_URL = "https://eyes.nasa.gov/dsn/data/dsn.xml"
MARS_CRAFT = {"MRO", "M01O", "MVN", "MSL", "M20", "TGO", "MEX"}   # orbiters and rovers at Mars
KEEP_S = 60
_cache = {}


def fetch():
    return requests.get(DSN_URL, timeout=5).text


def parse(text):
    """[{"dish", "craft", "round_trip_s"}] for the Mars spacecraft in one copy of the feed."""
    passes = []
    for dish in ET.fromstring(text).iter("dish"):
        for target in dish.iter("target"):
            try:
                round_trip_s = float(target.get("rtlt", ""))
            except ValueError:
                continue
            if target.get("name", "").upper() in MARS_CRAFT and math.isfinite(round_trip_s) and round_trip_s > 0:
                passes.append({"dish": dish.get("name"), "craft": target.get("name"), "round_trip_s": round_trip_s})
    return passes


def mars_passes():
    """(passes, a line saying where they came from). Asked at most once a minute."""
    if "at" not in _cache or time.monotonic() - _cache["at"] > KEEP_S:
        try:
            _cache.update(passes=parse(fetch()), note="NASA DSN Now, live")
        except (requests.RequestException, ET.ParseError):
            _cache.update(passes=[], note="NASA DSN Now could not be reached")
        _cache["at"] = time.monotonic()
    return _cache["passes"], _cache["note"]
