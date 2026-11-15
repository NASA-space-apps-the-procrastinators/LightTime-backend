"""The health log: the suits' minute packets and each sensor's lowest signal."""
from datetime import datetime

from common import models

SENSORS = ["chest_band", "ecg", "imu", "ppg", "thermistor"]


def test_the_log_lists_the_suits_packets_newest_first(morning):
    log = morning.get("/api/base/packets?limit=48").get_json()
    packets = log["packets"]
    stamps = [packet["ts"][:19] for packet in packets]
    assert len(packets) == 48 and stamps == sorted(stamps, reverse=True) and stamps[0] == "2026-11-14T06:29:00"
    assert log["simulated"] is True and log["transmitted_to_ground_today"] == 0
    assert {packet["crew_id"] for packet in packets} == {"C1", "C2", "C3", "C4"}
    assert sorted({packet["source"] for packet in packets}) == SENSORS
    assert all(packet["window_s"] == 60 and packet["sent_to_ground"] is False for packet in packets)
    morning.post("/api/base/alerts/A1/send")
    assert morning.get("/api/base/packets?limit=1").get_json()["transmitted_to_ground_today"] == 1


def test_only_a_hard_limit_is_judged_on_a_single_packet(morning):
    packets = morning.get("/api/base/packets?crew=C1&limit=6").get_json()["packets"]
    by_metric = {packet["metric"]: packet for packet in packets}
    assert set(by_metric) == {"hr", "resp", "spo2", "temp_c", "skin_temp_c", "activity_g"}
    oxygen, core, heart = by_metric["spo2"], by_metric["temp_c"], by_metric["hr"]
    assert (oxygen["baseline"], oxygen["rule"], oxygen["state"]) == ([96.0, 99.0], "< 94", "OK")
    assert (core["baseline"], core["rule"], core["state"]) == ([36.3, 36.9], "> 38.0", "OK")
    assert "state" not in heart and "rule" not in heart and heart["suit_id"] == "LT-01"


def test_a_poor_signal_is_a_recheck_whatever_the_value(morning):
    poor = morning.get("/api/base/packets?crew=C1&state=RECHECK").get_json()["packets"]
    assert {packet["ts"][:16] for packet in poor} == {"2026-11-13T07:58", "2026-11-13T08:28", "2026-11-13T15:45"}
    assert all(packet["signal_quality"] < 0.6 and "rule" not in packet for packet in poor)
    assert morning.get("/api/base/packets?crew=C9").status_code == 400
    assert morning.get("/api/base/packets?state=FINE").status_code == 400


def test_the_log_never_shows_a_packet_from_after_the_ships_clock(morning):
    models.set_clock(datetime(2026, 11, 14, 3, 0))
    newest = morning.get("/api/base/packets?limit=1").get_json()["packets"][0]
    assert newest["ts"][:16] == "2026-11-14T03:00"


def test_stream_health_gives_each_sensors_lowest_signal(morning):
    health = morning.get("/api/base/stream-health").get_json()
    assert health["window_minutes"] == 60 and health["simulated"] is True
    assert [sensor["source"] for sensor in health["sensors"]] == SENSORS
    assert all(sensor["state"] == "OK" and 0.6 <= sensor["lowest_signal_quality"] <= 1
               for sensor in health["sensors"])
