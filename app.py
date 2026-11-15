import os

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

from common import lighttime
from common.models import db, seed


def create_app(database_url=None, morning=None):
    load_dotenv()
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        database_url or os.getenv("DATABASE_URL", "sqlite:///lighttime.db"))
    # Morning mode loads the demo morning and starts the mission clock. Run one process only:
    # the clock lives in this process's memory.
    app.config["MORNING"] = os.getenv("LIGHTTIME_MORNING") == "1" if morning is None else morning
    CORS(app)
    db.init_app(app)

    from base_station.routes import bp as base_bp
    from command_center.routes import bp as earth_bp
    app.register_blueprint(base_bp, url_prefix="/api/base")
    app.register_blueprint(earth_bp, url_prefix="/api/earth")

    with app.app_context():
        db.create_all()
        seed()
        if app.config["MORNING"]:
            from base_station import morning as demo_morning
            demo_morning.load()
    lighttime.mars_seconds()    # ask JPL once now, so no screen waits on it later
    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000)
