"""The generated crew month, read once from data/processed (built by data/scripts/build_all.py).

The ship reads reference/ and anomalous/ only. clean/ is a healthy crew for testing tools, and
ground_truth/ and reports/ are the answer key: the ship must never see them."""
import csv
import functools
import os
from datetime import date

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
