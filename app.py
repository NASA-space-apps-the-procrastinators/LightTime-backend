import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

from common import dataset, lighttime
from common.models import db, seed, utcnow


def create_app(database_url=None, morning=None):
    load_dotenv()
    app = Flask(__name__)
    main_url = database_url or os.getenv("DATABASE_URL", "sqlite:///lighttime.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = main_url
    # Traffic stats outlive a deploy in their own database. With none set, or a database given
    # (as the tests do), they share the main one.
    stats_url = None if database_url else os.getenv("STATS_DATABASE_URL")
    app.config["SQLALCHEMY_BINDS"] = {"stats": stats_url or main_url}
    # Morning mode loads the demo morning and starts the mission clock. Run one process only:
    # the clock lives in this process's memory.
    app.config["MORNING"] = os.getenv("LIGHTTIME_MORNING") == "1" if morning is None else morning
    CORS(app)
    db.init_app(app)

    from base_station import console, log  # noqa: F401  (each adds its routes to the ship's blueprint)
    from base_station.routes import bp as base_bp
    from command_center.routes import bp as earth_bp
    from stats import models as stats_models  # noqa: F401  (its tables, for create_all)
    app.register_blueprint(base_bp, url_prefix="/api/base")
    app.register_blueprint(earth_bp, url_prefix="/api/earth")

    @app.errorhandler(404)
    @app.errorhandler(405)
    def api_error(error):
        """A path or method no route has: JSON on the API, as every route's own errors are."""
        if not request.path.startswith("/api/"):
            return error
        response = jsonify(error="not found" if error.code == 404 else "method not allowed")
        if error.code == 405:
            response.headers["Allow"] = ", ".join(error.valid_methods or [])
        return response, error.code

    with app.app_context():
        db.create_all()
        seed()
        if app.config["MORNING"]:
            from base_station import morning as demo_morning
            demo_morning.load()
        try:
            dataset.last_minutes()  # read the month's minute file now, so the first /packets is quick
        except OSError:
            app.logger.warning("the suits' minute file could not be read; /packets will try again")
    lighttime.mars_seconds()    # ask JPL once now, so no screen waits on it later
    lighttime.mars_seconds(dataset.mission_date(utcnow()))   # and for the mission date, which the dial uses
    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000)
