import hashlib
import json
import os

import pytest

from common import dataset
from common.models import Crew

READ = ["reference/mission", "reference/crew", "reference/baselines", "reference/link_windows",
        "anomalous/daily_summary", "anomalous/checkins", "anomalous/alerts_seed", "anomalous/messages",
        "anomalous/reminders", "anomalous/cabin_env", "anomalous/radiation_daily",
        "anomalous/space_weather_events"]


def test_the_files_the_ship_reads_are_the_build_they_say_they_are():
    folder = os.path.join(dataset.ROOT, "processed")
    with open(os.path.join(folder, "BUILD_INFO.json")) as f:
        expected = json.load(f)["outputs_sha256"]
    for name in READ:
        with open(os.path.join(folder, name + ".csv"), "rb") as f:
            found = hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()   # a Windows checkout adds \r
        assert found == expected[name + ".csv"], name


def test_the_ship_cannot_open_the_answer_key():
    for name in ("ground_truth/anomalies", "reports/replay_alerts_clean", "clean/daily_summary",
                 "reference/../clean/daily_summary", "anomalous/../../processed/ground_truth/anomalies",
                 "reference\\..\\clean\\daily_summary"):
        with pytest.raises(ValueError):
            dataset.table(name)


def test_the_ship_starts_with_the_four_crew_from_the_dataset(app):
    with app.app_context():
        crew = [(c.id, c.code, c.name, c.suit_id) for c in Crew.query.order_by(Crew.id)]
    assert crew == [(1, "C1", "TJ", "LT-01"), (2, "C2", "Rebecca", "LT-02"),
                    (3, "C3", "Kyler", "LT-03"), (4, "C4", "David", "LT-04")]


def test_a_reading_can_name_its_crew_member_either_way(client):
    by_code = client.post("/api/base/readings", json={"crew_id": "C2", "heart_rate": 70})
    by_number = client.post("/api/base/readings", json={"crew_id": 2, "heart_rate": 71})
    assert by_code.status_code == by_number.status_code == 201
    assert by_code.get_json()["reading"]["crew_id"] == by_number.get_json()["reading"]["crew_id"] == 2
    assert client.post("/api/base/readings", json={"crew_id": "C9", "heart_rate": 70}).status_code == 400
