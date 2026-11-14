"""The one command. Rebuilds everything under data/processed/ from the raw files.

    python data/scripts/build_all.py                 # seed 2026
    python data/scripts/build_all.py --seed 7        # another seeded variant
    python data/scripts/build_all.py --check-repro   # build twice, compare every file's hash
    python data/scripts/build_all.py --replay        # also replay both builds through the backend

Uses the standard library only (the replay needs the backend's requirements.txt).
"""
import argparse
import json
import subprocess
import sys
import time

import config as C
import generate_clean
import inject_anomalies
import summarise
import validate
from util import sha256


def outputs():
    return sorted(p for p in C.OUT.rglob("*.csv") if "reports" not in p.parts)


def build(seed):
    t = time.time()
    validate.check_manifest()
    if validate.fails:
        sys.exit("raw data changed: " + "; ".join(validate.fails))
    print(f"[1/4] clean build (seed {seed})")
    generate_clean.run(seed)
    print("[2/4] inject anomalies")
    inject_anomalies.run(seed)
    print("[3/4] daily summaries and packets")
    summarise.run(C.OUT_CLEAN, seed)
    summarise.run(C.OUT_ANOM, seed)
    print(f"      built in {time.time() - t:.0f} s")
    return {p.relative_to(C.OUT).as_posix(): sha256(p) for p in outputs()}


def git_head():
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=C.REPO, capture_output=True, text=True).stdout.strip()
    except OSError:
        return ""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=C.DEFAULT_SEED)
    p.add_argument("--check-repro", action="store_true")
    p.add_argument("--replay", action="store_true")
    a = p.parse_args()
    hashes = build(a.seed)
    repro = None
    if a.check_repro:
        print("rebuilding to check the output is byte-identical")
        again = build(a.seed)
        diff = sorted(k for k in hashes if hashes[k] != again.get(k))
        repro = "identical" if not diff else f"DIFFERENT: {diff}"
        print("reproducible:", repro)
    print("[4/4] validate")
    validate.fails.clear()
    validate.notes.clear()
    ok = validate.run()
    info = {"seed": a.seed, "git_head": git_head(), "demo_now": C.iso(C.DEMO_NOW),
            "raw_manifest_sha256": sha256(validate.MANIFEST), "outputs_sha256": hashes,
            "reproducible_check": repro, "validation": "PASS" if ok else "FAIL"}
    (C.OUT / "BUILD_INFO.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    if a.replay:
        import replay
        for b in ("clean", "anomalous"):
            replay.run(b)
    sys.exit(0 if ok and repro in (None, "identical") else 1)


if __name__ == "__main__":
    main()
