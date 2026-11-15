import pytest
import requests

from app import create_app
from base_station import usual
from common import dsn, lighttime, models
from stats import counter


def _offline(monkeypatch):
    def offline(*args):
        raise requests.ConnectionError("tests do not use the network")

    monkeypatch.setattr(lighttime, "fetch", offline)
    monkeypatch.setattr(dsn, "fetch", offline)
    lighttime._cache.clear()
    dsn._cache.clear()
    usual.clear()
    counter.clear()
    models.set_clock(None)


@pytest.fixture
def app(monkeypatch):
    _offline(monkeypatch)
    app = create_app("sqlite:///:memory:", morning=False)
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def morning(monkeypatch):
    """A client on the demo morning: 14 November 2026, 06:30 UTC, alert A1 just raised."""
    _offline(monkeypatch)
    app = create_app("sqlite:///:memory:", morning=True)
    app.config["TESTING"] = True
    yield app.test_client()
    models.set_clock(None)
