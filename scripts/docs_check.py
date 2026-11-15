"""Check the written documents before they are submitted. Run from the repo root:

    python scripts/docs_check.py                      README.md, docs/*.md, docs/tech/*.md, paper/sections/*.tex
    python scripts/docs_check.py docs/concept.md      one or more files

FAIL lines must be fixed. REVIEW lines are claims a mentor corrected on 15 November: read the
sentence and keep it only if it says what the note says. Exit code 1 if anything FAILs.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT = ["README.md", "docs/*.md", "docs/tech/*.md", "paper/sections/*.tex"]

FAIL = [
    ("\u2014", "em dash: use a comma, a period, parentheses or a new sentence"),
    (" \u2013 ", "en dash used as a dash: rewrite the sentence"),
    (r"Okafor|Rodenburg|Rebecca Qi|Adeyemi|Lindqvist|Mensah|\bSato\b",
     "old crew name: use the names in data/processed/reference/crew.csv and command_center/routes.py"),
    (r"11 min\w*[^.]{0,20}\bclosest", "11 minutes is our mission date, not Mars at its closest (3 to 22 min one way)"),
    (r"\b(4|four) to 24 min", "Mars one-way light time is about 3 to 22 minutes"),
    (r"bio-?monitor\W+vest", "the CSA Bio-Monitor is a smart shirt, not a vest"),
    (r"\bDSN\b[^.]{0,40}\b(measur|calculat|comput|monitor)\w*[^.]{0,30}\b(time|delay)",
     "the delay comes from JPL Horizons distance divided by the speed of light; the DSN carries the signal"),
    (r"\b(first|only)\b[^.]{0,30}\bhealth monitor", "novelty claim the background check does not support"),
    (r"(?<!no )(?<!trained )(?<!learned )\b(AI|model|LIGHTTIME)\s+(decides|diagnoses|prescribes)\b",
     "no model decides: rules decide, people act"),
]
REVIEW = [
    (r"\b40[ -]hours?\b", "sources disagree on CMO training hours (up to 40 in one NASA interview, about 15 in a NASA abstract)"),
    (r"\bsecure\b|\bsecurity\b", "role-based views are not a login; say what is and is not protected"),
    (r"NEWS2[^.]{0,60}\b(valid|proven|approved)", "NEWS2 is a hospital score, not validated in spaceflight"),
    (r"flight surgeon[^.]{0,60}\b(on board|onboard|aboard)\b|\b(on board|onboard|aboard)\b[^.]{0,60}flight surgeon",
     "the flight surgeon is on Earth; on board it is the crew medical officer"),
    (r"\bmachine learning\b|\bneural\b|\bdeep learning\b", "describe LIGHTTIME as rules and statistics; learned models only advise, offline"),
    (r"\bcontinuous(ly)?\b[^.]{0,40}\b(monitor|wear|stream)", "pair continuous monitoring with the stated assumption that the crew wear the shirt"),
]
LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def files(args):
    patterns = args or DEFAULT
    found = []
    for pattern in patterns:
        found += sorted(ROOT.glob(pattern)) if any(ch in pattern for ch in "*?[") else [ROOT / pattern]
    return [path for path in found if path.is_file()]


def broken_links(path, text):
    for target in LINK.findall(text):
        if re.match(r"(https?|mailto):|#", target):
            continue
        local = (path.parent / target.split("#")[0]).resolve()
        if not local.exists():
            yield target


def main(args):
    failed = 0
    for path in files(args):
        text = path.read_text(encoding="utf-8")
        name = path.relative_to(ROOT).as_posix()
        for number, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith(("http", "|  http")):
                continue
            for pattern, note in FAIL:
                if re.search(pattern, line, flags=re.IGNORECASE):
                    print(f"FAIL   {name}:{number}: {note}")
                    failed += 1
            for pattern, note in REVIEW:
                if re.search(pattern, line, flags=re.IGNORECASE):
                    print(f"REVIEW {name}:{number}: {note}")
        for target in broken_links(path, text):
            print(f"FAIL   {name}: broken link {target}")
            failed += 1
    print(f"{failed} to fix")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
