import os
import json
import traceback


from extensions import db
from models import VideoJob, User

from clipper.audio import extract_audio
from autosubtitle.whisper import transcribe_audio
from autosubtitle.sub_style import write_ass, get_attr
from autosubtitle.burn_sub import burn_subtitles

from helper.preview_download import generate_thumbnail

from clipper.tasks.worker_app import get_app

def process_autosubs_background(job_id, video_path, style):
    app = get_app()
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

            job.status = "failed"
            # Refund tokens
            if job.usage_charged:
                user.used_today = max(0, user.used_today - 1)
                job.usage_charged = False
        finally:
            db.session.commit()