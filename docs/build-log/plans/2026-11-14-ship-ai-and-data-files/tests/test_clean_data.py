from scripts.build_clean_data import align_wrist, clean_cabin, read_uw

HR = "100.0\n1.0\n60\n61\n75\n62\n"                       # starts 10 s after the temperature file
TEMP = "90.0\n4.0\n" + "32.0\n" * 56                        # 14 seconds at four values a second
ACTIVITY = "# SUBJECT_ID, S1\n# NO_ACTIVITY, 0\n# CYCLING, 11\n# NO_ACTIVITY, 12\n"


def test_wrist_rows_line_up_on_one_second_steps():
    rows = align_wrist(HR, TEMP, ACTIVITY)
    assert [r[0] for r in rows] == [10, 11, 12, 13]
    assert rows[0] == [10, 60.0, 32.0, "NO_ACTIVITY", "rest", 1]


def test_exercise_and_its_cool_down_are_marked():
    rows = align_wrist(HR, TEMP, ACTIVITY)
    assert [r[4] for r in rows] == ["rest", "exercise", "exercise", "exercise"]


def test_a_jump_no_body_can_make_is_flagged_not_deleted():
    rows = align_wrist(HR, TEMP, ACTIVITY)
    assert [r[5] for r in rows] == [1, 1, 0, 0]          # 61 to 75 bpm, then 75 to 62, in one second each
    assert len(rows) == 4


def test_cabin_rows_with_a_gap_are_dropped():
    telemetry = [{"time": "t1", "temperature_iss": 24.1, "humidity_iss": 39.0, "co2_iss": 2641.0},
                 {"time": "t2", "temperature_iss": None, "humidity_iss": 39.0, "co2_iss": 2642.0}]
    assert clean_cabin(telemetry) == [["t1", 24.1, 39.0, 2641.0]]


def test_the_oximeter_file_is_read_without_its_closing_line():
    text = "\ufeffTime,SpO2 5,Pulse 5\n09:25:02,98,57\n09:25:03,97,58\nCollection Halted,,\n"
    assert read_uw(text) == [[98.0, 57.0], [97.0, 58.0]]
