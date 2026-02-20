from .forms import ClipperFileForm
import os, tempfile,  shutil
from werkzeug.utils import secure_filename

from flask import Blueprint, render_template, session, jsonify, redirect, url_for, abort, send_from_directory


from clipper.tasks.clipper_tasks import process_video_background

from helper.preview_download import get_user_clip_with_outputs


from helper.daily_usage import can_start_job
#from helper.calculate_tokens import calculate_required_tokens
from datetime import date

from flask import json

from yt_dlp import YoutubeDL

from extensions import db
from extensions import clipper_queue
from models import VideoJob, User


clipper_bp = Blueprint("clipper", __name__ )

@clipper_bp.route("/auto-clipper")
def auto_clipper():

    form = ClipperFileForm()

    user_id = session.get("user_id")  # ✅ safe access

    if user_id:
        jobs = get_user_clip_with_outputs(user_id)
        return render_template(
            "autoClipper.html",
            form=form,
            jobs=jobs
            )
    else:
        jobs = []  # guest has no jobs

    return render_template(
        "guestClipper.html",
        form=form,
        jobs=jobs
    )


@clipper_bp.route('/clipper-video', methods = ["POST"])
def clipper():
    form = ClipperFileForm()
    if "user_id" not in session:
        return redirect(url_for("auth.register"))

    if not form.validate_on_submit():
        return jsonify({"error": "Invalid form"}), 400
    
    if not form.file.data and not form.video_url.data:
        return jsonify({"error": "Upload a file or paste a video link"}), 400
    
    # Get user
    user = User.query.get(session["user_id"])

    # SINGLE quota check
    if not can_start_job(user):
        return jsonify({"error": "Daily limit reached"}), 403

    db.session.commit()

    # Temp Directory
    BASE_TEMP_DIR = os.path.join(os.getcwd(), "uploads", "temp")
    os.makedirs(BASE_TEMP_DIR, exist_ok=True)
    job_dir = tempfile.mkdtemp(prefix="ffmpeg_", dir=BASE_TEMP_DIR)

    # Save Uploaded Video
    aspectRatio = form.aspectRatio.data
    subtitleStyle = form.subtitleStyle.data
    converted_path = os.path.join(job_dir, "aspect_converted.mp4")

    if form.file.data:
        file = form.file.data
        input_filename = secure_filename(file.filename)
        save_path = os.path.join(job_dir, input_filename)        
        file.save(save_path)


    elif form.video_url.data:
        save_path = download_from_link(
            form.video_url.data,
            job_dir
        )

    else:
        return jsonify({"error": "No video provided"}), 400

    
    # Now create VideoJob
    job = VideoJob(
        user_id=user.id,
        status="processing",
        progress=0,
        step="uploaded",
        job_dir=job_dir,
        original_filename=os.path.basename(save_path),
        job_type="clipper",
        usage_charged=False,
        aspect_ratio=aspectRatio,
        subtitle_style=subtitleStyle
    )

    db.session.add(job)
    db.session.commit()

    # RETURN job_id immediately
    job_id = job.id

    # Start background processing
    clipper_queue.enqueue(
    process_video_background,
    job_id,
    save_path,
    job_dir
)
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

@clipper_bp.route("/clip-thumbnail/<int:job_id>/<filename>")
def clip_thumbnail(job_id, filename):
    job = VideoJob.query.get_or_404(job_id)

    clip_dir = os.path.join(job.job_dir, "clips")

    return send_from_directory(clip_dir, filename)

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




