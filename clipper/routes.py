from .forms import ClipperFileForm
import os, tempfile, time, traceback, shutil
from werkzeug.utils import secure_filename
from threading import Thread

from flask import Blueprint, render_template, session, jsonify, redirect, url_for, abort, send_from_directory

from clipper.audio import extract_audio
from clipper.whisper import transcribe_audio
from clipper.nlp import merge_segments, detect_topic_changes, enforce_min_duration
from clipper.clipper import cut_topic_clips

from helper.preview_download import get_user_clip_with_outputs, generate_thumbnail_clip
from helper.aspect_ratio import convert_aspect

from helper.daily_usage import can_start_job
from helper.autosub import add_auto_subtitle_fast
#from helper.calculate_tokens import calculate_required_tokens
from datetime import date

from flask import current_app,json

from yt_dlp import YoutubeDL

from extensions import db
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
        user = User.query.get(job.user_id)

        
        aspect_ratio = job.aspect_ratio or "original"
        subtitle_style = job.subtitle_style or "default_portrait"

        if not job.usage_charged:
            user.used_today += 1
            job.usage_charged = True
            db.session.commit()
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

            job.transcript_data = json.dumps(segments)

            job.step = "transcribed"
            job.progress = 50
            db.session.commit()

            merged = merge_segments(segments, max_gap=0.6)
            job.progress = 70
            job.step = "analyzing topics"
            db.session.commit()
            topic_clips = detect_topic_changes(merged, threshold=0.85)

            topic_clips = enforce_min_duration(
                topic_clips,
                min_duration=30  # or 60
            )

            job.progress = 85
            job.step = "cutting clips"
            db.session.commit()
            final_clips = cut_topic_clips(
                video_path=save_path,
                clips=topic_clips,
                output_dir=job_dir + "/clips"
            )

            normalized_clips = []

            
            for clip in final_clips:
                abs_path = clip["file"]

                clip["file"] = os.path.basename(abs_path)

                normalized_clips.append(clip)

            final_clips = normalized_clips

            job.progress = 92
            job.step = "formatting clips"
            db.session.commit()

            if aspect_ratio != "original":
                converted_clips = []

                clips_dir = os.path.join(job_dir, "clips")

                for clip in final_clips:
                    # rebuild absolute path
                    clip_path = os.path.join(clips_dir, clip["file"])

                    converted = clip_path.replace(".mp4", "_converted.mp4")

                    convert_aspect(
                        input_path=clip_path,
                        output_path=converted,
                        ratio=aspect_ratio
                    )

                    os.replace(converted, clip_path)
                    converted_clips.append(clip)

                final_clips = converted_clips

            # ---------- AUTO SUBTITLE (FINAL STEP) ----------
            job.progress = 95
            job.step = "adding subtitles"
            db.session.commit()

            clips_dir = os.path.join(job_dir, "clips")

            if not job.transcript_data:
                print("Transcript exists:", bool(job.transcript_data))
                raise Exception("Transcript not available for this job")

            if job.transcript_data:
                segments = json.loads(job.transcript_data)
            else:
                # fallback (old jobs)
                audio_path = extract_audio(save_path, job_dir)
                segments = transcribe_audio(audio_path)

                job.transcript_data = json.dumps(segments)
                db.session.commit()

            for clip in final_clips:

                # always rebuild absolute path safely
                filename = os.path.basename(clip["file"])
                clip_path = os.path.join(clips_dir, filename)

                # unique temp workspace per clip
                safe_name = os.path.splitext(filename)[0]

                clip_temp_dir = os.path.join(
                    job_dir,
                    f"subs_{safe_name}"
                )
                os.makedirs(clip_temp_dir, exist_ok=True)

                # create subtitled video
                subtitled_path = add_auto_subtitle_fast(
                    video_path=clip_path,
                    clip_start=clip["start"],
                    clip_end=clip["end"],
                    segments=segments,
                    job_dir=clip_temp_dir,
                    style=subtitle_style
                )

                # ✅ replace original clip with subtitled version
                os.replace(subtitled_path, clip_path)

                # ✅ ensure DB keeps filename only
                clip["file"] = filename


            job.step = "creating thumbnails"
            db.session.commit()

            for clip in final_clips:
                clip_path = os.path.join(clips_dir, clip["file"])

                thumb_path = clip_path.replace(".mp4", ".jpg")

                generate_thumbnail_clip(clip_path, thumb_path)

                clip["thumbnail_name"] = os.path.basename(thumb_path)

            job.progress = 100
            job.step = "done"
            job.clips_data = json.dumps(final_clips)
            job.status = "finished"
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




