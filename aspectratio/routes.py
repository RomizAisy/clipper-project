from flask import Blueprint, render_template, current_app

import os, tempfile, time, traceback
from werkzeug.utils import secure_filename
from threading import Thread

from flask import Blueprint, render_template, session, jsonify, redirect, url_for, abort, send_from_directory, send_file

from .forms import AspectFileForm

from helper.preview_download import generate_thumbnail, get_user_jobs_with_outputs
from helper.aspect_ratio import convert_aspect
from helper.calculate_tokens import calculate_required_tokens

from yt_dlp import YoutubeDL

from extensions import db
from models import VideoJob, User



aspect_bp = Blueprint( "aspect", __name__)

@aspect_bp.route("/aspect-ratio")
def aspect_page():
    

    form = AspectFileForm()
    user_id = session.get("user_id")  # ✅ safe acces

    if user_id:
        jobs = get_user_jobs_with_outputs(user_id)
        return render_template(
        "aspectRatio.html",
        form=form,
        jobs=jobs
    )
    else:
        jobs = []  # guest has no jobs
    
    return render_template(
        "guestAspect.html",
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

    if form.file.data:
        file = form.file.data
        save_path = os.path.join(job_dir, secure_filename(file.filename))
        file.save(save_path)

    elif form.video_url.data:
        save_path = download_from_link(form.video_url.data, job_dir)
         

    else:
        return jsonify({"error": "No video provided"}), 400
    

    # Get user
    user = User.query.get(session["user_id"])

    # Calculate required tokens
    try:
        required_tokens = calculate_required_tokens(save_path)
    except Exception as e:
        return jsonify({"error": f"Could not read video duration: {str(e)}"}), 400

    # Check token balance
    if user.tokens < required_tokens:
        return jsonify({
            "error": "Not enough tokens",
            "required": required_tokens,
            "available": user.tokens
        }), 403

    # Deduct tokens
    try:
        user.tokens -= required_tokens
        db.session.commit()
    except:
        db.session.rollback()
        return jsonify({"error": "Token deduction failed"}), 500

    # Now create VideoJob
    job = VideoJob(
        user_id=user.id,
        status="processing",
        progress=0,
        step="uploaded",
        job_dir=job_dir,
        original_filename=os.path.basename(save_path),
        job_type="aspect",
        required_tokens=required_tokens
    )

    db.session.add(job)
    db.session.commit()

    # RETURN job_id immediately
    job_id = job.id

    # Start background processing
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

        try:
            # ---------- PROCESS ----------
            if ratio == "original":
                job.step = "skipped (original)"
                job.progress = 60
                output_path = input_path

            else:
                job.step = "converting"
                job.progress = 30
                db.session.commit()

                output_path = os.path.join(
                    job.job_dir,
                    "aspect_converted.mp4"
                )

                convert_aspect(
                    input_path=input_path,
                    output_path=output_path,
                    ratio=ratio
                )

            # ---------- SAVE OUTPUT ----------
            job.output_file = output_path
            db.session.commit()

            # ---------- THUMBNAIL ----------
            job.step = "generating preview"
            job.progress = 90
            db.session.commit()

            thumb = generate_thumbnail(output_path, job.job_dir)
            job.thumbnail_file = thumb

            # ---------- FINISH ----------
            job.status = "finished"
            job.progress = 100
            job.step = "done"
            db.session.commit()

        except Exception as e:
            traceback.print_exc()

            user = User.query.get(job.user_id)

            if user and job.required_tokens:
                user.tokens += job.required_tokens

            job.status = "failed, token refunded"
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


@aspect_bp.route("/aspect-status/<int:job_id>")
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

@aspect_bp.route("/aspect-thumbnail/<int:job_id>")
def aspect_thumbnail(job_id):
    job = VideoJob.query.get_or_404(job_id)

    if not job.thumbnail_file:
        abort(404)

    return send_file(job.thumbnail_file)

@aspect_bp.route("/aspect-stream/<int:job_id>")
def aspect_stream(job_id):
    if "user_id" not in session:
        abort(401)

    job = VideoJob.query.get_or_404(job_id)
    if job.user_id != session["user_id"]:
        abort(403)

    if not job.output_file or not os.path.exists(job.output_file):
        abort(404, "Output not ready")

    return send_file(
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

    return send_file(
        job.output_file,
        as_attachment=True,
        download_name="aspect_converted.mp4",
        mimetype="video/mp4"
    )
