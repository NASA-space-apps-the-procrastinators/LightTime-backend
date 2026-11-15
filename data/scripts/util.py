"""Small helpers shared by the build scripts: seeded random streams, CSV in and out
with fixed number formatting (so builds are byte-identical), and the link schedule."""
import csv
import hashlib
import math
import random
from bisect import bisect_right
from datetime import timedelta

import config as C

# Decimal places per column. Anything not listed is written as given.
DECIMALS = {
    "hr_bpm": 1, "resp_rpm": 1, "spo2_pct": 1, "skin_temp_c": 2, "core_temp_c": 2, "activity_g": 3,
    "bp_sys_est_mmhg": 1, "signal_quality": 2, "co2_ppm": 0, "co2_mmhg": 2, "ppo2_mmhg": 1,
    "pressure_kpa": 2, "temp_c": 1, "rh_pct": 0, "gcr_mgy": 5, "saa_mgy": 5, "sep_mgy": 5, "total_mgy": 5,
    "dose_msv_day": 3, "dose_msv_mission": 2, "hr_rest_bpm": 0, "bp_sys_mmhg": 0, "bp_dia_mmhg": 0,
    "sleep_h": 1, "sleep_h_suit": 1, "value": 2, "one_way_delay_s": 2, "delay_s": 2,
    "cuff_bp_sys_mmhg": 0, "cuff_bp_dia_mmhg": 0, "low": 2, "high": 2, "point": 2,
    "watch_param": 2, "alert_param": 2, "min_possible": 1, "max_possible": 1,
}


def rng(seed, *names):
    """An independent random stream per (seed, name...). Stable across Python runs."""
    key = "|".join([str(seed), *map(str, names)]).encode()
    return random.Random(int.from_bytes(hashlib.sha256(key).digest()[:8], "big"))


def fmt(name, value):
    if value is None or value == "":
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        d = DECIMALS.get(name, 3)
        return f"{value:.{d}f}"
    if isinstance(value, (list, tuple)):
        return "|".join(str(v) for v in value)
    return str(value)


def write_csv(path, columns, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(columns)
        for r in rows:
            w.writerow([fmt(c, r.get(c)) for c in columns])


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fnum(text):
    return None if text in ("", None) else float(text)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def smoothstep(t0, t1, t):
    """0 before t0, 1 after t1, smooth in between (datetimes)."""
    if t <= t0:
        return 0.0
    if t >= t1:
        return 1.0
    x = (t - t0) / (t1 - t0)
    return x * x * (3 - 2 * x)


def minutes(a, b):
    """Datetimes every minute from a (inclusive) to b (exclusive)."""
    t = a
    while t < b:
        yield t
        t += timedelta(minutes=1)


# ---- link schedule ----------------------------------------------------------
def load_light_time():
    rows = read_csv(C.REFERENCE_IN / "horizons_mars_light_time.csv")
    return {r["date"]: float(r["one_way_light_time_s"]) for r in rows}


def link_windows():
    """Daily windows: one per day while the link is up (that day's Horizons light time),
    one for the blackout."""
    light = load_light_time()
    out = []
    for wid, start, end, stop, up, note in C.LINK_WINDOWS:
        if not up:
            out.append({"window_id": "", "start": start, "end": end, "stop": stop, "link_up": False,
                        "one_way_delay_s": None, "delay_source": "none (link down)", "note": note})
            continue
        t = start
        while t < end:
            nxt = min(end, (t + timedelta(days=1)).replace(hour=0, minute=0, second=0))
            out.append({"window_id": "", "start": t, "end": nxt, "stop": stop, "link_up": True,
                        "one_way_delay_s": light[t.date().isoformat()],
                        "delay_source": "JPL Horizons q21, data/reference/horizons_mars_light_time.csv",
                        "note": note})
            t = nxt
    for i, w in enumerate(out, 1):
        w["window_id"] = f"W{i:03d}"
    return out


class Link:
    def __init__(self):
        self.windows = link_windows()
        self.starts = [w["start"] for w in self.windows]

    def at(self, t):
        i = bisect_right(self.starts, t) - 1
        return self.windows[max(0, i)]

    def up(self, t):
        return self.at(t)["link_up"]

    def next_up(self, t):
        """Earliest time at or after t when the link is up."""
        w = self.at(t)
        while not w["link_up"]:
            t = w["end"]
            w = self.at(t)
        return t

    def send(self, created):
        """(sent_at, delay_s, deliver_at) for a message created at `created`."""
        sent = self.next_up(created)
        delay = self.at(sent)["one_way_delay_s"]
        return sent, delay, sent + timedelta(seconds=delay)


def status_at(sent, deliver, now=C.DEMO_NOW):
    if sent is None or sent > now:
        return "queued"
    return "delivered" if deliver <= now else "in_flight"
