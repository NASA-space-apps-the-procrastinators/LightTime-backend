"""Every outside source the app uses, in one list: for the Data panel and for the judges."""
from common import lighttime

SOURCES = [
    {"id": "horizons", "agency": "NASA JPL", "name": "Horizons ephemeris system", "kind": "live",
     "url": "https://ssd.jpl.nasa.gov/api/horizons.api",
     "used_for": "Mars light time. It sets the delay on every message and who decides."},
    {"id": "dsn", "agency": "NASA", "name": "Deep Space Network Now", "kind": "live",
     "url": "https://eyes.nasa.gov/dsn/data/dsn.xml",
     "used_for": "Round-trip light time NASA measures to its Mars spacecraft. A second check on the delay."},
    {"id": "eda", "agency": "NASA", "name": "Open Science Data Repository, environmental data, mission RR-1 on the ISS",
     "kind": "file", "url": "https://visualization.osdr.nasa.gov/eda/",
     "used_for": "Cabin temperature, humidity, carbon dioxide and radiation dose."},
    {"id": "hrp", "agency": "NASA", "name": "Human Research Program risk list", "kind": "hand",
     "url": "https://www.nasa.gov/hrp/risks/", "used_for": "The risk name on every alert."},
    {"id": "ppg_dalia", "agency": "UCI Machine Learning Repository", "name": "PPG-DaLiA", "kind": "file",
     "url": "https://archive.ics.uci.edu/dataset/495/ppg+dalia",
     "used_for": "Heart rate and skin temperature replayed as the suit stream."},
    {"id": "spo2_uw", "agency": "University of Washington", "name": "Induced hypoxemia oximeter recordings",
     "kind": "file", "url": "https://github.com/ubicomplab/oximetry-phone-cam-data",
     "used_for": "The recorded fall in blood oxygen, and the test of the time-left rule."},
    {"id": "apnea_ecg", "agency": "PhysioNet", "name": "Apnea-ECG Database", "kind": "file",
     "url": "https://physionet.org/content/apnea-ecg/1.0.0/",
     "used_for": "False-alarm test of the blood-oxygen rules."},
]
AS_OF = {"file": "In the repo, see data/", "hand": "Copied by hand, see docs/data-sources.md",
         "live": "Asked when a screen needs it"}


def listing():
    """The list, each with a line saying how fresh it is."""
    return [{**s, "as_of": lighttime.source() if s["id"] == "horizons" else AS_OF[s["kind"]]} for s in SOURCES]
