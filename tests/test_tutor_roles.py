"""Tutors and the coordinator: one tutor per learner, by name; only the coordinator sees analytics and
the interview accommodation requests (disability information)."""
import pytest
from fastapi.testclient import TestClient

from tests.test_channels_handoff import client  # noqa: F401  (fixture: temporary databases)


@pytest.fixture()
def desk(client, monkeypatch):  # noqa: F811
    """Two tutors and a coordinator, each with their own browser (cookies)."""
    monkeypatch.setenv("TUTORS", "Hana:hana-pw, Abel:abel-pw")
    monkeypatch.setenv("ADMIN_PASSWORD", "coord-pw")
    from server.main import app

    def signed_in(name, password):
        browser = TestClient(app)
        reply = browser.post("/handoff/console/login", data={"name": name, "password": password}, follow_redirects=False)
        assert reply.status_code == 303, (name, reply.status_code)
        return browser

    return {"hana": signed_in("hana", "hana-pw"), "abel": signed_in("Abel", "abel-pw"),
            "coordinator": signed_in("Selam", "coord-pw"), "learner": client}


def new_ticket(learner):
    return learner.post("/handoff/tickets", json={"lang": "am", "conversation": [{"role": "user", "text": "help"}]}).json()["ticket_id"]


def test_each_person_signs_in_with_their_own_name_and_role(desk):
    assert desk["hana"].get("/handoff/api/me").json() == {"role": "tutor", "name": "Hana"}  # name as configured
    assert desk["coordinator"].get("/handoff/api/me").json() == {"role": "admin", "name": "Selam"}


def test_wrong_passwords_are_refused(desk):
    learner = desk["learner"]
    assert learner.post("/handoff/console/login", data={"name": "Hana", "password": "abel-pw"}).status_code == 401
    assert learner.post("/handoff/console/login", data={"name": "Nobody", "password": "x"}).status_code == 401
    # The old shared password no longer opens the console once ADMIN_PASSWORD is set.
    assert learner.post("/handoff/console/login", data={"password": "test-password"}).status_code == 401


def test_a_forged_session_is_refused(desk):
    forged = TestClient(desk["learner"].app)
    forged.cookies.set("tutor_session", "admin|Mallory|0000")
    assert forged.get("/handoff/api/me").status_code == 401


def test_take_this_request_one_tutor_per_learner(desk):
    from server.handoff import tickets

    ticket = new_ticket(desk["learner"])
    assert desk["hana"].post(f"/handoff/tickets/{ticket}/claim").json() == {"claimed": True, "tutor": "Hana"}
    # The learner is told who is helping, in their language.
    assert tickets.messages(ticket)[-1]["text"] == "Hana (አስተማሪ) ተቀላቅለዋል፤ ይረዱዎታል።"
    # Another tutor is refused, and told who has it.
    refused = desk["abel"].post(f"/handoff/tickets/{ticket}/claim")
    assert refused.status_code == 409 and refused.json()["claimed_by"] == "Hana"
    # Taking it again is harmless; the list shows who has it.
    assert desk["hana"].post(f"/handoff/tickets/{ticket}/claim").status_code == 200
    listed = {t["id"]: t["tutor_name"] for t in desk["abel"].get("/handoff/api/tickets").json()["tickets"]}
    assert listed[ticket] == "Hana"


def test_the_coordinator_can_take_over(desk):
    from server.handoff import tickets

    ticket = new_ticket(desk["learner"])
    desk["hana"].post(f"/handoff/tickets/{ticket}/claim")
    assert desk["coordinator"].post(f"/handoff/tickets/{ticket}/claim").json()["tutor"] == "Selam"
    assert tickets.get_ticket(ticket)["tutor_name"] == "Selam"


def test_opening_the_live_chat_takes_a_free_request_and_refuses_a_taken_one(desk):
    from starlette.websockets import WebSocketDisconnect

    from server.handoff import tickets

    ticket = new_ticket(desk["learner"])
    with desk["abel"].websocket_connect(f"/handoff/ws/{ticket}?role=tutor") as ws:
        assert ws.receive_json()["type"] == "history"
    assert tickets.get_ticket(ticket)["tutor_name"] == "Abel"  # opening it took it
    with desk["hana"].websocket_connect(f"/handoff/ws/{ticket}?role=tutor") as ws:
        assert ws.receive_json() == {"type": "taken", "by": "Abel"}
        with pytest.raises(WebSocketDisconnect):
            ws.receive_json()
    # The coordinator may watch without taking it.
    with desk["coordinator"].websocket_connect(f"/handoff/ws/{ticket}?role=tutor") as ws:
        assert ws.receive_json()["type"] == "history"
    assert tickets.get_ticket(ticket)["tutor_name"] == "Abel"


def test_only_the_coordinator_sees_analytics_and_accommodation_requests(desk):
    desk["learner"].post("/accommodation", data={"job_text": "Job", "support": "Sign language interpreter", "contact": "x@example.org", "lang": "en"})
    tutor_view = desk["hana"].get("/handoff/api/dashboard").json()
    assert tutor_view["accommodations"] == [] and tutor_view["teacher"] is None and tutor_view["me"]["role"] == "tutor"
    coordinator_view = desk["coordinator"].get("/handoff/api/dashboard").json()
    assert coordinator_view["accommodations"] and coordinator_view["teacher"] is not None
    # The accommodation page itself.
    assert desk["hana"].get("/accommodation/requests", follow_redirects=False).status_code == 303
    assert "Sign language interpreter" in desk["coordinator"].get("/accommodation/requests").text
    assert desk["hana"].post("/accommodation/requests/1/done").status_code == 403


def test_without_tutor_accounts_the_shared_password_still_works(client):  # noqa: F811
    """Existing setups (only TUTOR_PASSWORD) keep working: it signs in as the coordinator."""
    reply = client.post("/handoff/console/login", data={"password": "test-password"}, follow_redirects=False)
    assert reply.status_code == 303
    assert client.get("/handoff/api/me").json() == {"role": "admin", "name": "Coordinator"}


def test_console_links_never_point_at_a_laptop():
    from pathlib import Path

    for name in ("handoff_console.html", "handoff_login.html"):
        assert "localhost" not in (Path(__file__).resolve().parents[1] / "server" / "templates" / name).read_text(encoding="utf-8")


def test_mimi_offers_interview_support_about_jobs():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "module"
    assert "accommodation?lang=" in (root / "db-assistant.js").read_text(encoding="utf-8")
    for code in ("en", "am", "om"):
        assert json.loads((root / "i18n" / f"{code}.json").read_text(encoding="utf-8"))["accommodationChip"]
