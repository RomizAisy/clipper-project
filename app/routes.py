from flask import Blueprint, render_template, session
from flask_wtf import FlaskForm

from extensions import db
from models import User
from clipper.forms import ClipperFileForm

from helper.preview_download import (
    get_user_jobs_with_outputs,
    get_user_clip_with_outputs,
)
from helper.cleanup_job import cleanup_old_jobs
from helper.daily_usage import get_daily_limit_left


main_bp = Blueprint("main", __name__)


class CSRFOnlyForm(FlaskForm):
    pass


@main_bp.route("/")
def home():
    form = CSRFOnlyForm()
    user = None
    tokens = 0
    jobs_autosub = []
    jobs_aspect = []
    jobs_all = []
    daily_left = 0

    if "user_id" in session:
        user = User.query.filter_by(username=session["username"]).first()
        user_obj = db.session.get(User, session["user_id"])

        cleanup_old_jobs(days=5)

        if user_obj:
            tokens = user_obj.tokens
            daily_left = get_daily_limit_left(user)
            db.session.commit()

            jobs_clipper = get_user_clip_with_outputs(session["user_id"])

            jobs_all = get_user_jobs_with_outputs(session["user_id"])
            for item in jobs_all:
                job = item["job"]
                if job.job_type == "autosub":
                    jobs_autosub.append(item)
                elif job.job_type == "aspect":
                    jobs_aspect.append(item)

        return render_template(
            "dashboard.html",
            user=user,
            jobs=jobs_all,
            tokens=tokens,
            jobs_clipper=jobs_clipper,
            jobs_autosub=jobs_autosub,
            jobs_aspect=jobs_aspect,
            daily_left=daily_left,
            form=form,
        )

    clipper_form = ClipperFileForm()

    return render_template(
        "home.html",
        user=user,
        tokens=tokens,
        jobs_autosub=jobs_autosub,
        jobs_aspect=jobs_aspect,
        jobs_clipper=[],
        clipper_form=clipper_form,
        form=form,
    )