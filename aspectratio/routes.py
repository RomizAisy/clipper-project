from flask import Blueprint, render_template, current_app

import os, tempfile, time
from werkzeug.utils import secure_filename
from threading import Thread

from flask import Blueprint, render_template, session, jsonify, redirect, url_for, abort, send_from_directory

from .forms import AspectFileForm

from helper.preview_download import get_user_jobs_with_outputs
from helper.aspect_ratio import convert_aspect

from yt_dlp import YoutubeDL

from extensions import db
from models import VideoJob



aspect_bp = Blueprint( "aspect", __name__)

@aspect_bp.route("/aspect-ratio")
def aspect_page():
    if "user_id" not in session:
        return redirect("/login")

    form = AspectFileForm()
    jobs = get_user_jobs_with_outputs(session["user_id"])
    
    return render_template(
        "aspectRatio.html",
        form=form,
        jobs=jobs
    )

@aspect_bp.route("/aspect-change", methods = ["POST", "GET"])
def aspect_ratio():
    form = AspectFileForm()
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    if not form.validate_on_submit():
        return jsonify({"error": "Invalid form"}), 400
    
    if not form.file.data and not form.video_url.data:
        return jsonify({"error": "Upload a file or paste a video link"}), 400

    # Temp Directory
    BASE_TEMP_DIR = os.path.join(os.getcwd(), "uploads", "temp")
    os.makedirs(BASE_TEMP_DIR, exist_ok=True)
    job_dir = tempfile.mkdtemp(prefix="ffmpeg_", dir=BASE_TEMP_DIR)

    # Save Uploaded Video
    aspectRatio = form.aspectRatio.data
    converted_path = os.path.join(job_dir, "aspect_converted.mp4")

    if form.file.data:
        file = form.file.data
        save_path = os.path.join(job_dir, secure_filename(file.filename))
        file.save(save_path)

    elif form.video_url.data:
        save_path = download_from_link(form.video_url.data, job_dir)

    else:
        return jsonify({"error": "No video provided"}), 400
    

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
    job_id = job.id
    app = current_app._get_current_object()

    Thread(
        target=process_aspect_background,
        args=(app, job_id, save_path, aspectRatio),
        daemon=True
    ).start()

    return jsonify({"job_id": job_id})

def process_aspect_background(app, job_id, input_path, ratio):
    with app.app_context():
        job = VideoJob.query.get(job_id)
        if not job:
            return
        if ratio == "original":
            job.step = "skipped (original)"
            job.output_file = input_path
            job.status = "finished"
            job.progress = 100
            db.session.commit()
            return

        try:
            job.step = "converting"
            job.progress = 30
            db.session.commit()

            output_path = os.path.join(job.job_dir, "aspect_converted.mp4")

            convert_aspect(
                input_path=input_path,
                output_path=output_path,
                ratio=ratio
            )

            job.output_file = output_path
            job.progress = 100
            job.status = "finished"
            job.step = "done"
            db.session.commit()

        except Exception as e:
            job.status = "failed"
            job.step = str(e)
            db.session.commit()

    
def download_from_link(url, job_dir):
    output = os.path.join(job_dir, "input.%(ext)s")

    ydl_opts = {
        "format": "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[ext=mp4]",
        "outtmpl": output,
        "quiet": True,
        "noplaylist": True,
        "merge_output_format": "mp4"
    }

    MAX_SECONDS = 60 * 60   #60 minutes 

    with YoutubeDL(ydl_opts) as ydl:
        # Get info WITHOUT downloading first
        info = ydl.extract_info(url, download=False)

        duration = info.get("duration", 0)

        if duration > MAX_SECONDS:
            mins = duration // 60
            raise ValueError(f"Video too long ({mins} minutes). Max allowed is X minutes.")

        # ⬇ Now download if safe
        info = ydl.extract_info(url, download=True)
        ext = info.get("ext", "mp4")

    return os.path.join(job_dir, f"input.{ext}")


@aspect_bp.route("/clipper-status/<int:job_id>")
def aspect_status(job_id):
    if "user_id" not in session:
        abort(401)

    job = VideoJob.query.get(job_id)
    if not job:
        return jsonify({"status": "not_found"}), 404

    if job.user_id != session["user_id"]:
        abort(403)

    return jsonify({
        "status": job.status,
        "progress": job.progress,
        "step": job.step,
        "job_id": job.id
    })

@aspect_bp.route("/aspect-stream/<int:job_id>")
def aspect_stream(job_id):
    if "user_id" not in session:
        abort(401)

    job = VideoJob.query.get_or_404(job_id)
    if job.user_id != session["user_id"]:
        abort(403)

    if not job.output_file or not os.path.exists(job.output_file):
        abort(404, "Output not ready")

    return send_from_directory(
        job.output_file,
        mimetype="video/mp4"
    )



@aspect_bp.route("/aspect-download/<int:job_id>")
def aspect_download(job_id):
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
