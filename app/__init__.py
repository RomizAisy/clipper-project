import os
from flask import Flask
from dotenv import load_dotenv, find_dotenv

from config import Config
from extensions import db, migrate, mail

# blueprints
from .routes import main_bp
from auth import auth_bp
from payment import payment_bp
from clipper import clipper_bp
from autosubtitle import autosub_bp
from aspectratio import aspect_bp
from music import music_bp



load_dotenv(find_dotenv())


def create_app():
    app = Flask(__name__,
                template_folder="../templates",
                 static_folder="../static"
                )
    app.config.from_object(Config)

    app.secret_key = app.config["SECRET_KEY"]
    app.permanent_session_lifetime = app.config["PERMANENT_SESSION_LIFETIME"]

    # ---------- extensions ----------
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)

    # ---------- blueprints ----------
    app.register_blueprint(auth_bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(clipper_bp)
    app.register_blueprint(autosub_bp)
    app.register_blueprint(aspect_bp)
    app.register_blueprint(music_bp)



    # register routes AFTER app exists
    app.register_blueprint(main_bp)

    return app