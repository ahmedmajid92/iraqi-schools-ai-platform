import os
from flask import Flask
from dotenv import load_dotenv

from .db import init_db

def create_app() -> Flask:
    load_dotenv()

    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")

    # sqlite db in instance folder
    instance_path = os.path.join(os.path.dirname(__file__), "..", "instance")
    os.makedirs(instance_path, exist_ok=True)
    app.config["DB_PATH"] = os.path.join(instance_path, "app.sqlite3")

    init_db(app.config["DB_PATH"])

    from .routes import bp
    app.register_blueprint(bp)

    return app
