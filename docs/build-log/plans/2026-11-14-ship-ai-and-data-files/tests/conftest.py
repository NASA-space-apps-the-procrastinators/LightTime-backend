import pytest
import requests

from app import create_app
from base_station import usual
from common import lighttime


@pytest.fixture
def app(monkeypatch):
    def offline(day):
        raise requests.ConnectionError("tests do not use the network")

    monkeypatch.setattr(lighttime, "fetch", offline)
    lighttime._cache.clear()
    usual.clear()
    app = create_app("sqlite:///:memory:")
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()
