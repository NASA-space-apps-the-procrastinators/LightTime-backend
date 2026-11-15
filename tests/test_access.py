"""Who may read whose health record on the ship (base_station/access.py)."""
from base_station import access

EVERYONE = ["C1", "C2", "C3", "C4"]


def as_(code):
    return {access.HEADER: code}


def sos(client):
    for _ in range(5):
        out = client.post("/api/base/readings", json={"crew_id": "C1", "spo2": 86}).get_json()
    return out["alerts"][0]


def test_no_viewer_is_the_medical_station_and_sees_every_record(client):
    board = client.get("/api/base/crew").get_json()
    assert [c["id"] for c in board] == EVERYONE
    assert all(c["restricted"] is False and "today" in c for c in board)
    assert [c["is_cmo"] for c in board] == [False, True, False, False]


def test_a_crew_member_sees_their_own_record_and_only_names_for_the_rest(client):
    board = client.get("/api/base/crew", headers=as_("C3")).get_json()
    assert [c["id"] for c in board] == EVERYONE
    mine = board[2]
    assert mine["restricted"] is False and "today" in mine and "baseline" in mine
    for other in (board[0], board[1], board[3]):
        assert other["restricted"] is True
        assert set(other) == {"id", "name", "role", "suit_id", "is_cmo", "restricted"}


def test_the_crew_medical_officer_sees_every_record(client):
    board = client.get("/api/base/crew", headers=as_("C2")).get_json()
    assert all(c["restricted"] is False and "today" in c for c in board)
    assert client.get("/api/base/crew/C1/history?metric=hr_rest", headers=as_("C2")).status_code == 200


def test_another_persons_record_is_refused_by_every_door(client):
    for path in ("/api/base/crew/C1", "/api/base/crew/C1/history?metric=hr_rest", "/api/base/crew/C1/readings"):
        refused = client.get(path, headers=as_("C3"))
        assert refused.status_code == 403, path
        assert refused.get_json() == {"error": access.REFUSAL, "field": "viewer"}
    for path in ("/api/base/crew/C3", "/api/base/crew/C3/history?metric=hr_rest", "/api/base/crew/C3/readings"):
        assert client.get(path, headers=as_("C3")).status_code == 200, path
    assert client.get("/api/base/crew/C1?viewer=c3").status_code == 403      # the query form, any case


def test_an_sos_reaches_everyone_but_only_as_who_and_what(client):
    alert = sos(client)
    seen = client.get("/api/base/alerts", headers=as_("C3")).get_json()
    assert [a["id"] for a in seen] == [alert["id"]]
    notice = seen[0]
    assert notice["restricted"] is True and notice["crew"] == "TJ" and notice["level"] == "emergency"
    assert notice["vital"] == "spo2"
    for private in ("value", "reason", "why", "symptoms", "lookahead", "speak", "steps"):
        assert private not in notice, private
    one = client.get(f"/api/base/alerts/{alert['id']}", headers=as_("C3")).get_json()
    assert set(one) == set(notice) and one["restricted"] is True
    assert client.get(f"/api/base/alerts/{alert['id']}/thread", headers=as_("C3")).status_code == 403
    full = client.get("/api/base/alerts", headers=as_("C2")).get_json()[0]
    assert full["restricted"] is False and full["value"] == 86 and full["steps"]
    assert client.get("/api/base/alerts", headers=as_("C1")).get_json()[0]["value"] == 86   # the patient


def test_a_quiet_alert_about_someone_else_is_not_shown_at_all(morning):
    everything = morning.get("/api/base/alerts").get_json()
    quiet = [a for a in everything if a["level"] != "emergency"]
    assert quiet, "the demo morning has no alert below an SOS to test with"
    seen = morning.get("/api/base/alerts", headers=as_("C3")).get_json()
    assert all(a["crew_id"] == "C3" or a["level"] == "emergency" for a in seen)
    other = next(a for a in quiet if a["crew_id"] != "C3")
    assert morning.get(f"/api/base/alerts/{other['id']}", headers=as_("C3")).status_code == 403


def test_the_packet_log_shows_a_crew_member_only_their_own_suit(morning):
    packets = morning.get("/api/base/packets?limit=400", headers=as_("C3")).get_json()["packets"]
    assert packets and {p["suit_id"] for p in packets} == {"LT-03"}
    everyone = morning.get("/api/base/packets?limit=400").get_json()["packets"]
    assert len({p["suit_id"] for p in everyone}) > 1
