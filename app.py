import os
from flask import Flask
from flask import render_template, redirect, request, session, flash, jsonify

from config import Config

from extensions import db, migrate, mail

from models import User, Admin, Transaction
from clipper.forms import ClipperFileForm

from auth import auth_bp
from payment import payment_bp
from clipper import clipper_bp
from autosubtitle import autosub_bp
from aspectratio import aspect_bp
from music import music_bp



from helper.preview_download import get_user_jobs_with_outputs, get_user_clip_with_outputs
from helper.cleanup_job import cleanup_old_jobs

from dotenv import load_dotenv, find_dotenv



from flask_wtf import FlaskForm



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

class CSRFOnlyForm(FlaskForm):
    pass

@app.route('/')
def home():
    form = CSRFOnlyForm()
    user = None
    tokens = 0
    jobs_autosub = []
    jobs_aspect = []

    if "user_id" in session:
        user = User.query.filter_by(username=session["username"]).first()
        user_obj = db.session.get(User, session["user_id"])

        cleanup_old_jobs(days=5)

        if user_obj:
            tokens = user_obj.tokens

            # Only get clipper jobs as objects (with .file and .thumbnail_name)
            jobs_clipper = get_user_clip_with_outputs(session["user_id"])

            # Get other jobs (autosub/aspect) if needed
            jobs_all = get_user_jobs_with_outputs(session["user_id"])
            for item in jobs_all:
                job = item['job']
                if job.job_type == "autosub":
                    jobs_autosub.append(item)
                elif job.job_type == "aspect":
                    jobs_aspect.append(item)

        return render_template(
            "dashboard.html",
            user=user,
            jobs = jobs_all,
            tokens=tokens,
            jobs_clipper=jobs_clipper,  # ready-to-use clipper jobs
            jobs_autosub=jobs_autosub,
            jobs_aspect=jobs_aspect,
            form=form
        )

    # Guest view
    clipper_form = ClipperFileForm()
    return render_template(
        "home.html",
        user=user,
        tokens=tokens,
        jobs_autosub=jobs_autosub,
        jobs_aspect=jobs_aspect,
        jobs_clipper=[],
        clipper_form=clipper_form,
        form=form
    )




if __name__ == "__main__":
    app.run(
        debug=True,
        port=5001
    )