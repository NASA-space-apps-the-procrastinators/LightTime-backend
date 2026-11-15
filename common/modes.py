"""The four dial stops and the rule for who decides."""
from common import lighttime, link

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
SHIP_AI = {
    "name": "LIGHTTIME",
    "line": "It knows how long the light takes, so it knows who has to act.",
    "version": "rules 2026-11-14",
    "parts": [
        {"name": "Don't cry wolf", "does": "Throws out junk signal. Every alarm rule was first tried on real recordings."},
        {"name": "Know each person", "does": "Learns each person's usual range from their own last 24 hours."},
        {"name": "Time left", "does": "Works out how long until a falling reading is critical, and whether Earth can answer first."},
        {"name": "Ask ahead", "does": "Answers the flight surgeon's first questions before the report leaves."},
    ],
}
ROLE = {
    "doctor_live": "Drafts the report. The flight surgeon directs care.",
    "crew_first": "Coaches the crew medical officer. Earth reviews afterwards.",
    "ship_alone": "Main reference until the link returns. Everything is kept for Earth.",
}


def mode_for(delay_s, link_up):
    if not link_up:
        return "ship_alone"
    if delay_s >= CREW_FIRST_AT_S:
        return "crew_first"
    return "doctor_live"


def describe(stop):
    """One dial stop with its working: the delay, the path it stands for, the round trip,
    and how long one leg takes on the demo clock."""
    fixed = stop in FIXED_DELAY_S
    delay_s = FIXED_DELAY_S[stop] if fixed else lighttime.mars_seconds()
    link_up = STOPS[stop]["link_up"]
    mode = mode_for(delay_s, link_up)
    return {
        "stop": stop, "label": STOPS[stop]["label"], "link_up": link_up, "delay_s": delay_s,
        "mode": mode, "who_decides": WHO_DECIDES[mode],
        "ship_ai_role": ROLE[mode],
        "light_time_source": "fixed" if fixed else lighttime.source(),
        "path_km": round(lighttime.path_km(delay_s)), "round_trip_s": 2 * delay_s,
        "plays_as_s": link.real_delay_s(delay_s),
    }
