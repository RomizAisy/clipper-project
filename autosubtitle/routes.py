from flask import Blueprint, json, render_template, redirect, send_file, session, jsonify, abort, send_from_directory, flash, request, url_for


from helper.daily_usage import can_start_job
from .forms import AutosubFileForm
from werkzeug.utils import secure_filename

import os, tempfile, time, traceback, shutil
from threading import Thread

from clipper.audio import extract_audio
from autosubtitle.whisper import transcribe_audio
from autosubtitle.sub_style import write_ass, get_attr
from autosubtitle.burn_sub import burn_subtitles

from helper.preview_download import get_user_jobs_with_outputs, generate_thumbnail
from helper.aspect_ratio import convert_aspect
from helper.calculate_tokens import calculate_required_tokens


from yt_dlp import YoutubeDL

from extensions import db
from models import VideoJob, User

from flask import current_app

autosub_bp = Blueprint("autosub", __name__)


@autosub_bp.route("/auto-subtitle")
def autosub_page():

    form = AutosubFileForm()

    user_id = session.get("user_id")  # ✅ safe access

    if user_id:
        jobs = get_user_jobs_with_outputs(user_id)
        return render_template(
        "autoSubtitle.html",
        form=form,
        jobs=jobs
    )
    else:
        jobs = []  # guest has no jobs

    return render_template(
        "guestSubtitle.html",
        form=form,
        jobs=jobs
    )

@autosub_bp.route("/add-subtitle", methods = ["POST"])
def add_subtitle():
    form = AutosubFileForm()
    user = User.query.get(session["user_id"])

    if "user_id" not in session:
        return redirect(url_for("auth.register"))

    if not form.validate_on_submit():
        return jsonify({"error": "Invalid form"}), 400
    
    if not form.file.data and not form.video_url.data:
        return jsonify({"error": "Upload a file or paste a video link"}), 400
    
    if not can_start_job(user):
        return jsonify({"error": "Daily limit reached"}), 403

    # Temp Directory
    BASE_TEMP_DIR = os.path.join(os.getcwd(), "uploads", "temp")
    os.makedirs(BASE_TEMP_DIR, exist_ok=True)
    job_dir = tempfile.mkdtemp(prefix="ffmpeg_", dir=BASE_TEMP_DIR)

    # Save Uploaded Video

    style = form.subtitleStyle.data
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
            convert_aspect(
                input_path=save_path,
                output_path=converted_path,
                ratio=aspectRatio
            )
            # remove original
            if os.path.exists(save_path):
                os.remove(save_path)
            save_path = converted_path

    else:
        return jsonify({"error": "No video provided"}), 400

    # Get user
   

    # Now create VideoJob
    job = VideoJob(
        user_id=user.id,
        status="processing",
        progress=0,
        step="uploaded",
        job_dir=job_dir,
        original_filename=os.path.basename(save_path),
        job_type="autosub",
        usage_charged=False,
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

def process_autosubs_background(app, job_id, video_path, style):
    with app.app_context():
        job = VideoJob.query.get(job_id)
        user = User.query.get(job.user_id)
        if not job.usage_charged:
            user.used_today += 1
            job.usage_charged = True
            db.session.commit()

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

            audio_path = extract_audio(video_path, job.job_dir)

            segments, info = transcribe_audio(audio_path)
            if not segments:
                raise Exception("No subtitle segments returned")

            segments = [
                s for s in segments
                if get_attr(s, "start") is not None
                and get_attr(s, "end") is not None
            ]

            if not segments:
                raise Exception("No valid subtitle segments")

            job.transcript_data = json.dumps(segments)

            job.step = "transcribed"
            job.progress = 50
            db.session.commit()


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
            job.output_file = output_path

            burn_subtitles(video_path, ass_path, output_path)


            # -----------------------------
            # GENERATE THUMBNAIL
            # -----------------------------
            job.step = "generating preview"
            job.progress = 95
            db.session.commit()

            thumb = generate_thumbnail(output_path, job.job_dir)
            job.thumbnail_file = thumb

            # -----------------------------
            # FINISH JOB
            # -----------------------------
            job.progress = 100
            job.status = "finished"
            job.step = "done"
            db.session.commit()

        except Exception as e:

            traceback.print_exc()

            user = User.query.get(job.user_id)
            job.status = "failed"
            # Refund tokens
            if job.usage_charged:
                user.used_today = max(0, user.used_today - 1)
                job.usage_charged = False
        finally:
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
        "step": job.step,
        "job_id": job.id
    })

@autosub_bp.route("/thumbnail/<int:job_id>")
def autosub_thumbnail(job_id):
    job = VideoJob.query.get_or_404(job_id)

    return send_file(job.thumbnail_file, mimetype="image/jpeg")

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


