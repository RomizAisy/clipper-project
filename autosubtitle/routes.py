from flask import Blueprint, render_template, redirect, session, jsonify, abort, send_file, send_from_directory
from .forms import AutosubFileForm
from werkzeug.utils import secure_filename

import os, tempfile, time, traceback, shutil
from threading import Thread

from clipper.audio import extract_audio
from autosubtitle.whisper import transcribe_audio
from autosubtitle.sub_style import write_ass
from autosubtitle.burn_sub import burn_subtitles




from extensions import db
from models import VideoJob

from helper.preview_download import get_user_jobs_with_clips

from flask import current_app

autosub_bp = Blueprint("autosub", __name__)


@autosub_bp.route("/auto-subtitle")
def autosub_page():
    if "user_id" not in session:
        return redirect("/login")

    form = AutosubFileForm()
    jobs = get_user_jobs_with_clips(session["user_id"])
    
    return render_template(
        "autoSubtitle.html",
        form=form,
        jobs=jobs
    )

@autosub_bp.route("/add-subtitle", methods = ["POST"])
def add_subtitle():
    form = AutosubFileForm()
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    if not form.validate_on_submit():
        return jsonify({"error": "Invalid form"}), 400

    # Temp Directory
    BASE_TEMP_DIR = os.path.join(os.getcwd(), "uploads", "temp")
    os.makedirs(BASE_TEMP_DIR, exist_ok=True)
    job_dir = tempfile.mkdtemp(prefix="ffmpeg_", dir=BASE_TEMP_DIR)

    # Save Uploaded Video
    file = form.file.data
    style = form.subtitleStyle.data
    input_filename = secure_filename(file.filename)
    save_path = os.path.join(job_dir, input_filename)
    file.save(save_path)

     # Create VideoJob in DB immediately
    job = VideoJob(
        user_id=session["user_id"],
        status="processing",
        progress=0,
        step="uploaded",
        job_dir=job_dir
    )
    db.session.add(job)
    db.session.commit()

    # RETURN job_id immediately
    job_id = job.id

    # Start background processing
    app = current_app._get_current_object()
    Thread(
        target=process_autosubs_background,
        args=(app, job_id, save_path, style),
        daemon=True
    ).start()
    return jsonify({"job_id": job_id})

def fake_progress(app, job_id, start, end, duration=60):
    with app.app_context():
        steps = 10
        step_time = duration / steps
        inc = (end - start) / steps

        for i in range(steps):
            job = VideoJob.query.get(job_id)
            if not job or job.status != "processing":
                break

            new_progress = int(start + inc * (i + 1))

            # don't overwrite real progress
            if new_progress > job.progress:
                job.progress = new_progress
                job.step = "transcribing"
                db.session.commit()

            time.sleep(step_time)

def process_autosubs_background(app, job_id, video_path, style):
    with app.app_context():
        job = VideoJob.query.get(job_id)
        if not job:
            return

        try:
            job.status = "processing"
            job.step = "extracting audio"
            job.progress = 10
            db.session.commit()

            audio_path = os.path.join(job.job_dir, "audio.wav")
            ass_path   = os.path.join(job.job_dir, "subs.ass")
            output_path = os.path.join(
                job.job_dir,
                f"subtitled_{os.path.basename(video_path)}"
            )
            print("Extracting audio to:", audio_path)
            audio_path = extract_audio(video_path, job.job_dir)

            job.step = "transcribing"
            job.progress = 30
            db.session.commit()

            segments, info = transcribe_audio(audio_path)

            job.step = "generating subtitles"
            job.progress = 55
            db.session.commit()

            write_ass(segments, ass_path, style)

            job.step = "burning subtitles"
            job.progress = 80
            db.session.commit()

            output_dir = os.path.join(job.job_dir, "output")
            os.makedirs(output_dir, exist_ok=True)

            output_path = os.path.join(output_dir, "subtitled.mp4")

            burn_subtitles(video_path, ass_path, output_path)

            job.progress = 100
            job.status = "finished"
            job.step = "done"
            db.session.commit()

        except Exception as e:
            job.status = "failed"
            traceback.print_exc()
            job.step = str(e)
            db.session.commit()

@autosub_bp.route("/autosub-status/<int:job_id>")
def autosub_status(job_id):
    if "user_id" not in session:
        abort(401)

    job = VideoJob.query.get_or_404(job_id)

    if job.user_id != session["user_id"]:
        abort(403)

    return jsonify({
        "status": job.status,
        "progress": job.progress,
        "step": job.step
    })

@autosub_bp.route("/autosub-stream/<int:job_id>")
def autosub_stream(job_id):
    if "user_id" not in session:
        abort(401)

    job = VideoJob.query.get_or_404(job_id)
    if job.user_id != session["user_id"]:
        abort(403)

    output_dir = os.path.join(job.job_dir, "output")
    filename = "subtitled.mp4"

    if not os.path.exists(os.path.join(output_dir, filename)):
        abort(404, "Output not ready")

    return send_from_directory(
        output_dir,
        filename,
        mimetype="video/mp4"
    )



@autosub_bp.route("/autosub-download/<int:job_id>")
def autosub_download(job_id):
    if "user_id" not in session:
        abort(401)

    job = VideoJob.query.get_or_404(job_id)
    if job.user_id != session["user_id"]:
        abort(403)

    output_dir = os.path.join(job.job_dir, "output")

    return send_from_directory(
        output_dir,
        "subtitled.mp4",
        as_attachment=True,
        mimetype="video/mp4"
    )

@autosub_bp.route("/autosub-delete/<int:job_id>", methods=["POST"])
def autosub_delete(job_id):
    if "user_id" not in session:
        abort(401)

    job = VideoJob.query.get_or_404(job_id)
    if job.user_id != session["user_id"]:
        abort(403)

    # Delete files
    if job.job_dir and os.path.exists(job.job_dir):
        shutil.rmtree(job.job_dir, ignore_errors=True)

    # Delete DB record
    db.session.delete(job)
    db.session.commit()

    return jsonify({"message": "Auto subtitle job deleted"})


