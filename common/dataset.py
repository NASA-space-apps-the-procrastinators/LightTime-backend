"""The generated crew month, read once from data/processed (built by data/scripts/build_all.py).

The ship reads reference/ and anomalous/ only. clean/ is a healthy crew for testing tools, and
ground_truth/ and reports/ are the answer key: the ship must never see them."""
import csv
import functools
import os
from datetime import date, datetime, timedelta

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
ALLOWED = ("reference", "anomalous")


@functools.lru_cache(maxsize=None)
def table(name):
    """The rows of data/processed/<name>.csv as dicts, for example table("reference/crew")."""
    parts = name.split("/")
    if parts[0] not in ALLOWED or ".." in parts or "\\" in name:
        raise ValueError(f"the ship does not read {name}")
    with open(os.path.join(ROOT, "processed", name + ".csv"), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@functools.lru_cache(maxsize=None)
def last_minutes(hours=24):
    """The suits' minute rows for the last `hours` before the demo morning, oldest first.
    The file holds a month (168,600 rows). The log needs a day, so the rest is read past, not kept."""
    stop = datetime.fromisoformat(mission()["demo_now"].replace("Z", ""))
    since = (stop - timedelta(hours=hours)).isoformat()
    with open(os.path.join(ROOT, "processed", "anomalous", "vitals_1min.csv"), newline="", encoding="utf-8") as f:
        rows = [row for row in csv.DictReader(f) if row["sensor_ts"] >= since]
    return sorted(rows, key=lambda row: (row["sensor_ts"][:19], row["crew_id"]))


def num(text):
    return None if text in ("", None) else float(text)


def listed(text):
    """A cell like "headache|short sleep" as a list."""
    return [item for item in (text or "").split("|") if item]


def mission():
    return table("reference/mission")[0]


@functools.lru_cache(maxsize=None)
def last_day():
    return max(row["date"] for row in table("anomalous/daily_summary"))


def mission_date(now):
    """The mission date as text. The dataset stops on its last day, so a later clock shows that day."""
    return min(now.date().isoformat(), last_day())


def mission_day(now):
    """Day 1 is the launch date."""
    return (now.date() - date.fromisoformat(mission()["launch_date"])).days + 1
