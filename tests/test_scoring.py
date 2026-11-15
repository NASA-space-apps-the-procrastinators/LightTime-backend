from base_station import scoring

BAND = [52, 64]


def test_a_value_inside_the_persons_band_is_ok():
    assert scoring.score("hr_rest", 60, BAND, 0, False) == "OK"


def test_out_of_band_once_is_a_watch_and_three_days_or_a_symptom_make_it_an_alert():
    assert scoring.score("hr_rest", 80, BAND, 1, False) == "WATCH"
    assert scoring.score("hr_rest", 84, BAND, 3, False) == "ALERT"
    assert scoring.score("hr_rest", 80, BAND, 1, True) == "ALERT"


def test_three_limits_alert_on_their_own():
    assert scoring.score("spo2", 93, [96, 99], 0, False) == "ALERT"
    assert scoring.score("temp_c", 38.1, [36.3, 36.9], 0, False) == "ALERT"
    assert scoring.score("dose_mSv_day", 2.4, None, 0, False) == "ALERT"


def test_each_measurement_goes_out_of_range_its_own_way():
    assert scoring.score("spo2", 100, [96, 99], 0, False) == "OK"           # only low oxygen counts
    assert scoring.score("temp_c", 36.0, [36.3, 36.9], 0, False) == "OK"    # only a high temperature counts
    assert scoring.score("resp", 21, [12, 16], 0, False) == "WATCH"
    assert scoring.score("resp", 18, [12, 16], 0, False) == "OK"            # the band is not the rule for breathing
    assert scoring.score("sleep_h", 6.4, [6.0, 7.0], 0, False) == "WATCH"   # under 6.5 h, even inside the band
    assert scoring.score("mood", 2, None, 0, False) == "WATCH"
    assert scoring.score("pvt_ms", 312, None, 0, True, pvt_baseline=265) == "ALERT"
    assert scoring.score("pvt_ms", 300, None, 0, True, pvt_baseline=265) == "OK"
    assert scoring.score("dose_mSv_day", 1.9, None, 0, True) == "OK"
    assert scoring.score("mood", None, None, 0, False) is None              # nothing measured, nothing judged


def test_days_out_of_band_count_back_from_today_and_the_rules_have_their_words():
    assert scoring.days_out_of_band([60, 59, 58, 59, 80, 82, 84], BAND) == 3
    assert scoring.days_out_of_band([80, 60, 84], BAND) == 1
    assert scoring.days_out_of_band([80, None, 84], BAND) == 1
    assert scoring.worst(["OK", "ALERT", "WATCH"]) == "ALERT" and scoring.worst([]) == "OK"
    text = scoring.rule_text()
    assert text["hr_rest"]["unit"] == "bpm" and text["co2_mmHg"]["source"] and "pending" not in str(text)
