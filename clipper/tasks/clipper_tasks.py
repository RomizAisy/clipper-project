import os
import json
import traceback

from extensions import db
from models import VideoJob, User

from clipper.clipper import cut_topic_clips
from clipper.audio import extract_audio
from clipper.whisper import transcribe_audio
from clipper.nlp import merge_segments, detect_topic_changes, enforce_min_duration  
from clipper.tasks.fake_progress import fake_progress
from clipper.tasks.worker_app import get_app

from helper.aspect_ratio import convert_aspect
from helper.autosub import add_auto_subtitle_fast
from helper.preview_download import generate_thumbnail_clip


def process_video_background(job_id, save_path, job_dir):

    app = get_app()
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

            job.status = "failed"
            job.step = str(e)

            if job.usage_charged:
                user.used_today = max(0, user.used_today - 1)
                job.usage_charged = False

            db.session.commit()
            raise   # ⭐ VERY IMPORTANT
            # Refund tokens

