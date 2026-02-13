import os
from flask import Flask
from flask import render_template, redirect, request, session, flash, jsonify

from config import Config

from extensions import db, migrate, mail

from models import User, Admin, Transaction

from auth import auth_bp
from payment import payment_bp
from clipper import clipper_bp
from autosubtitle import autosub_bp
from aspectratio import aspect_bp
from music import music_bp



from helper.preview_download import get_user_jobs_with_outputs
from helper.cleanup_job import cleanup_old_jobs

from dotenv import load_dotenv, find_dotenv





load_dotenv(find_dotenv())

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = app.config["SECRET_KEY"]
app.permanent_session_lifetime = app.config["PERMANENT_SESSION_LIFETIME"]
app.register_blueprint(auth_bp)
app.register_blueprint(payment_bp)
app.register_blueprint(clipper_bp)
app.register_blueprint(autosub_bp)
app.register_blueprint(aspect_bp)
app.register_blueprint(music_bp)

db.init_app(app)
migrate.init_app(app, db)
mail.init_app(app)

@app.route('/')
def home():
    user = None
    tokens = 0
    jobs = [] 
    
    if "user_id" in session:
        user = User.query.filter_by(username=session["username"]).first()
        cleanup_old_jobs(days=5)
        if user:
            tokens = user.tokens
        jobs = get_user_jobs_with_outputs(session["user_id"])
        
    return render_template("home.html", user=user, tokens=tokens, jobs = jobs)



if __name__ == "__main__":
    app.run(
        debug=True,
        port=5001
    )