"""The four dial stops and the rule for who decides."""
from common import lighttime

# NASA's NEEMO 16 test (Rader et al. 2013): at about five minutes one way,
# critical medical advice cannot always get through.
CREW_FIRST_AT_S = 300

STOPS = {
    "station": {"label": "Space station", "link_up": True},
    "moon": {"label": "Moon", "link_up": True},
    "mars": {"label": "Mars", "link_up": True},
    "sun": {"label": "Behind the Sun", "link_up": False},
}
FIXED_DELAY_S = {"station": 0.25, "moon": 1.3}
WHO_DECIDES = {
    "doctor_live": "Flight surgeon on Earth",
    "crew_first": "Crew medical officer",
    "ship_alone": "The crew, alone",
}


def mode_for(delay_s, link_up):
    if not link_up:
        return "ship_alone"
    if delay_s >= CREW_FIRST_AT_S:
        return "crew_first"
    return "doctor_live"


def describe(stop):
    fixed = stop in FIXED_DELAY_S
    delay_s = FIXED_DELAY_S[stop] if fixed else lighttime.mars_seconds()
    link_up = STOPS[stop]["link_up"]
    mode = mode_for(delay_s, link_up)
    return {
        "stop": stop, "label": STOPS[stop]["label"], "link_up": link_up, "delay_s": delay_s,
        "mode": mode, "who_decides": WHO_DECIDES[mode],
        "light_time_source": "fixed" if fixed else lighttime.source(),
    }
