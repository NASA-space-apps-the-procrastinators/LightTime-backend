import pytest
import requests

from app import create_app
from base_station import usual
from common import dsn, lighttime, models


@pytest.fixture
def app(monkeypatch):
    def offline(*args):
        raise requests.ConnectionError("tests do not use the network")

    monkeypatch.setattr(lighttime, "fetch", offline)
    monkeypatch.setattr(dsn, "fetch", offline)
    lighttime._cache.clear()
    dsn._cache.clear()
    usual.clear()
    models.set_clock(None)
    app = create_app("sqlite:///:memory:")
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()
