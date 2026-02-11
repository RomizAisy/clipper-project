from .forms import ClipperFileForm
import os, tempfile, time
from werkzeug.utils import secure_filename
from threading import Thread

from flask import Blueprint, render_template, session, jsonify, redirect, url_for, abort, send_from_directory

from clipper.audio import extract_audio
from clipper.whisper import transcribe_audio
from clipper.nlp import merge_segments, detect_topic_changes, enforce_min_duration
from clipper.clipper import cut_topic_clips

from helper.preview_download import get_user_jobs_with_outputs
from helper.aspect_ratio import convert_aspect
from helper.calculate_tokens import calculate_required_tokens

from flask import current_app

from yt_dlp import YoutubeDL

from extensions import db
from models import VideoJob, User


clipper_bp = Blueprint("clipper", __name__ )

@clipper_bp.route("/auto-clipper")
def auto_clipper():
    if "user_id" not in session:
        return redirect("/login")

    form = ClipperFileForm()
    jobs = get_user_jobs_with_outputs(session["user_id"])
    
    return render_template(
        "autoClipper.html",
        form=form,
        jobs=jobs
    )


@clipper_bp.route('/clipper-video', methods = ["POST"])
def clipper():
    form = ClipperFileForm()
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
        input_filename = secure_filename(file.filename)
        save_path = os.path.join(job_dir, input_filename)        
        file.save(save_path)

        if aspectRatio and aspectRatio != "original":
            try:
                convert_aspect(
                    input_path=save_path,
                    output_path=converted_path,
                    ratio=aspectRatio
                )
                save_path = converted_path   
            except Exception as e:
                return jsonify({"error": f"Aspect ratio conversion failed: {str(e)}"}), 500

    elif form.video_url.data:
        save_path = download_from_link(
            form.video_url.data,
            job_dir
        )
        
        if aspectRatio and aspectRatio != "original":
            try:
                convert_aspect(
                    input_path=save_path,
                    output_path=converted_path,
                    ratio=aspectRatio
                )

                # optionally delete original to save space
                # os.remove(save_path)

                save_path = converted_path   # continue pipeline with converted video

            except Exception as e:
                return jsonify({
                    "error": f"Aspect ratio conversion failed: {str(e)}"
                }), 500

    else:
        return jsonify({"error": "No video provided"}), 400

    # Create VideoJob in DB immediately
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
        required_tokens=required_tokens
    )

    db.session.add(job)
    db.session.commit()# Get user
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
        required_tokens=required_tokens
    )

    db.session.add(job)
    db.session.commit()

    # RETURN job_id immediately
    job_id = job.id

    # Start background processing
    app = current_app._get_current_object()
    Thread(
        target=process_video_background,
        args=(app, job_id, save_path, job_dir),
        daemon=True
    ).start()
    return jsonify({"job_id": job_id})

MAX_SECONDS = 60 * 60   #60 minutes 

def download_from_link(url, job_dir):
    output = os.path.join(job_dir, "input.%(ext)s")

    ydl_opts = {
        "format": "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[ext=mp4]",
        "outtmpl": output,
        "quiet": True,
        "noplaylist": True,
        "merge_output_format": "mp4"
    }

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
    

def process_video_background(app, job_id, save_path, job_dir):
    
    with app.app_context():
        job = VideoJob.query.get(job_id)
        if not job:
            return
        try:
            audio_path = extract_audio(save_path, job_dir)
            job.progress = 25
            job.step = "audio_extracted"
            db.session.commit()

            Thread(
                target=fake_progress,
                args=(app, job_id, 30, 60, 90),
                daemon=True
            ).start()

            segments = transcribe_audio(audio_path)
            job.step = "transcribed"
            db.session.commit()

            merged = merge_segments(segments, max_gap=0.6)
            job.progress = 70
            job.step = "analyzing topics"
            db.session.commit()
            topic_clips = detect_topic_changes(merged, threshold=0.85)

            job.progress = 85
            job.step = "cutting clips"
            db.session.commit()
            final_clips = cut_topic_clips(
                video_path=save_path,
                clips=topic_clips,
                output_dir=job_dir + "/clips"
            )

            job.progress = 100
            job.step = "done"
            job.status = "finished"
            db.session.commit()

        except Exception as e:
            job.status = "failed"
            job.step = str(e)
            db.session.commit()

@clipper_bp.route("/clipper-status/<int:job_id>")
def clipper_status(job_id):
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


@clipper_bp.route("/clipper-stream/<int:job_id>/<filename>")
def clipper_stream(job_id, filename):
    if "user_id" not in session:
        abort(401)

    job = VideoJob.query.get_or_404(job_id)

    if job.user_id != session["user_id"]:
        abort(403)

    clips_dir = os.path.join(job.job_dir, "clips")

    return send_from_directory(
        clips_dir,
        filename,
        mimetype="video/mp4"
    )

@clipper_bp.route("/clipper-download/<int:job_id>/<filename>")
def clipper_download(job_id, filename):
    if "user_id" not in session:
        abort(401)

    job = VideoJob.query.get_or_404(job_id)
    if job.user_id != session["user_id"]:
        abort(403)

    clips_dir = os.path.join(job.job_dir, "clips")

    return send_from_directory(
        clips_dir,
        filename,
        as_attachment=True
    )

import shutil
from flask import abort, jsonify

@clipper_bp.route("/clipper-delete/<int:job_id>", methods=["POST"])
def delete_job(job_id):
    if "user_id" not in session:
        abort(401)

    job = VideoJob.query.get_or_404(job_id)

    # 🔐 Security: only owner can delete
    if job.user_id != session["user_id"]:
        abort(403)

    # 📁 Delete files safely
    if job.job_dir and os.path.exists(job.job_dir):
        shutil.rmtree(job.job_dir, ignore_errors=True)

    # 🗄 Delete DB record
    db.session.delete(job)
    db.session.commit()

    return jsonify({"message": "Job deleted"})
