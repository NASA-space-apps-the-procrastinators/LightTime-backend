from base_station import habitat


def test_the_first_cabin_row_is_nasas_first_reading():
    now = habitat.at(0)
    assert now["cabin"] == {"temp_c": 24.1, "humidity_pct": 39.0, "co2_ppm": 2641.0, "as_of": "2014-09-20T03:59:00Z"}
    assert now["radiation"] is None and now["kind"] == "file"       # dose records start the next day


def test_a_later_row_carries_that_days_radiation_dose():
    later = habitat.at(habitat.STEP_S * 300)                           # 300 five-minute rows = 25 hours on
    assert later["cabin"]["as_of"].startswith("2014-09-21")
    assert later["radiation"]["total_mgy_day"] == 0.20553


def test_the_cabin_data_loops(client):
    assert habitat.at(habitat.STEP_S * 12087)["cabin"] == habitat.at(0)["cabin"]
    assert client.get("/api/base/habitat").get_json()["source"].startswith("NASA OSDR")
