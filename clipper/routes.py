from .forms import ClipperFileForm
import os, tempfile, time
from werkzeug.utils import secure_filename
from threading import Thread

from flask import Blueprint, render_template, session, jsonify, redirect, url_for, abort, send_from_directory

from clipper.audio import extract_audio
from clipper.whisper import transcribe_audio
from clipper.nlp import merge_segments, detect_topic_changes, enforce_min_duration
from clipper.clipper import cut_topic_clips

from helper.preview_download import get_user_jobs_with_clips

from flask import current_app

from extensions import db
from models import VideoJob


clipper_bp = Blueprint("clipper", __name__ )

@clipper_bp.route("/auto-clipper")
def auto_clipper():
    if "user_id" not in session:
        return redirect("/login")

    form = ClipperFileForm()
    jobs = get_user_jobs_with_clips(session["user_id"])
    
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

    # Temp Directory
    BASE_TEMP_DIR = os.path.join(os.getcwd(), "uploads", "temp")
    os.makedirs(BASE_TEMP_DIR, exist_ok=True)
    job_dir = tempfile.mkdtemp(prefix="ffmpeg_", dir=BASE_TEMP_DIR)

    # Save Uploaded Video
    file = form.file.data
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
        target=process_video_background,
        args=(app, job_id, save_path, job_dir),
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

            merged = merge_segments(segments)
            job.progress = 70
            job.step = "analyzing topics"
            db.session.commit()
            topic_clips = detect_topic_changes(merged, threshold=0.65)
            topic_clips = enforce_min_duration(topic_clips, min_duration=30.0)

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
