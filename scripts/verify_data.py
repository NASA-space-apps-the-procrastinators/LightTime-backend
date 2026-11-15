"""Check the data and the light-time numbers. Run from the repo root:

    python scripts/verify_data.py            every check, including the two NASA services
    python scripts/verify_data.py --offline  skip the checks that need the network
    python scripts/verify_data.py --write    record the checksums of the raw files (do this once)
"""
import csv
import hashlib
import pathlib
import statistics
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from base_station.rules import LIMITS           # noqa: E402
from common import dsn, lighttime, modes        # noqa: E402

DATA, SUMS = ROOT / "data", ROOT / "data" / "CHECKSUMS.sha256"
RAW = ("ppg_dalia", "eda", "spo2_uw", "spo2_apnea_ecg")
NEWS2 = {   # typed from the NEWS2 chart (Royal College of Physicians, 2017)
    "spo2": [[91, 3], [93, 2], [95, 1], [None, 0]],
    "heart_rate": [[40, 3], [50, 1], [90, 0], [110, 1], [130, 2], [None, 3]],
    "bp_sys": [[90, 3], [100, 2], [110, 1], [219, 0], [None, 3]],
}
failed = []


def check(name, ok, detail=""):
    if not ok:
        failed.append(name)
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))


def rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def digest(path):
    """sha256 with Windows line endings folded, so the same file gives the same sum on every laptop."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def raw_files():
    return sorted(p for folder in RAW for p in (DATA / folder).rglob("*") if p.is_file())


if __name__ == "__main__":
    if "--write" in sys.argv:
        SUMS.write_text("".join(f"{digest(p)}  {p.relative_to(DATA).as_posix()}\n" for p in raw_files()))
        print(f"wrote {len(raw_files())} checksums to {SUMS.relative_to(ROOT)}")
        sys.exit(0)

    print("Light time")
    check("1 AU is 499.005 s of light", abs(lighttime.AU_KM / lighttime.C_KM_S - 499.0048) < 0.0001)
    check("Moon figure matches 384,400 km", abs(384_400 / lighttime.C_KM_S - modes.FIXED_DELAY_S["moon"]) < 0.05)
    check("Station figure matches a relay path of 2 x 35,786 km",
          abs(2 * 35_786 / lighttime.C_KM_S - modes.FIXED_DELAY_S["station"]) < 0.05)
    check("Crew-first line is five minutes", modes.CREW_FIRST_AT_S == 300)
    if "--offline" not in sys.argv:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        live = lighttime.fetch(today)
        check("Horizons answers, and Mars is inside its orbit limits", 0.372 * 499 <= live <= 2.68 * 499,
              f"{live:.2f} s one way, {live / 60:.2f} min, {live * lighttime.C_KM_S / 1e6:.1f} million km")
        if today in lighttime.FALLBACK_S:
            check("Saved fallback matches live Horizons", abs(live - lighttime.FALLBACK_S[today]) < 1,
                  f"saved {lighttime.FALLBACK_S[today]}")
        passes = dsn.parse(dsn.fetch())
        if passes:
            measured = statistics.median(p["round_trip_s"] for p in passes) / 2
            check("DSN Now agrees with Horizons within 10 s", abs(measured - live) < 10,
                  f"DSN {measured:.1f} s from {', '.join(p['craft'] for p in passes)}")
        else:
            print("SKIP  DSN Now: no antenna is on Mars this minute. Run again later.")

    print("Rules")
    for vital, bands in NEWS2.items():
        check(f"{vital} bands are the NEWS2 chart", LIMITS["vitals"][vital]["bands"] == bands)
    check("Heart rate cannot raise an alarm", LIMITS["vitals"]["heart_rate"].get("alert") is False)

    print("Clean tables")
    wrist = sorted((DATA / "clean" / "wrist").glob("S*.csv"))
    check("15 wrist files", len(wrist) == 15)
    for path in wrist:
        table = rows(path)
        rates, temps = [float(r["heart_rate"]) for r in table], [float(r["skin_temp"]) for r in table]
        flagged = sum(r["signal_ok"] == "0" for r in table)
        check(f"{path.stem}: heart rate and skin temperature are possible, few flags",
              30 <= min(rates) and max(rates) <= 230 and 20 <= min(temps) and max(temps) <= 42 and flagged <= 5,
              f"{len(table)} s, {min(rates):.0f} to {max(rates):.0f} bpm, {flagged} flagged")
    cabin = rows(DATA / "clean" / "cabin_rr1.csv")
    check("Cabin: 12,087 rows, all values possible",
          len(cabin) == 12087 and all(15 <= float(r["temp_c"]) <= 35 and 10 <= float(r["humidity_pct"]) <= 80
                                      and 300 <= float(r["co2_ppm"]) <= 8000 for r in cabin))
    doses = rows(DATA / "clean" / "radiation_rr1.csv")
    check("Radiation: 39 days, each under 2 mGy", len(doses) == 39 and all(0 < float(r["total_mgy_day"]) < 2 for r in doses))
    event = [float(r["spo2"]) for r in rows(DATA / "clean" / "spo2_event.csv")]
    check("Oxygen event: 769 s, 98 down to 67 and back to 96",
          len(event) == 769 and event[0] == 98 and min(event) == 67 and event[-1] == 96)

    print("Raw files")
    if SUMS.exists():
        known = dict(line.split("  ", 1)[::-1] for line in SUMS.read_text().splitlines())
        now = {p.relative_to(DATA).as_posix(): digest(p) for p in raw_files()}
        changed = [name for name in known if now.get(name) != known[name]]
        check(f"{len(known)} raw files unchanged since the checksums were written", not changed, ", ".join(changed[:3]))
    else:
        check("Checksums exist (run with --write once)", False)
    top = (DATA / "README.md").read_text(encoding="utf-8") if (DATA / "README.md").exists() else ""
    for folder in RAW:
        check(f"{folder} says where it came from", (DATA / folder / "README.md").exists() or folder in top)

    print(f"\n{'ALL CHECKS PASSED' if not failed else str(len(failed)) + ' FAILED: ' + '; '.join(failed)}")
    sys.exit(1 if failed else 0)
