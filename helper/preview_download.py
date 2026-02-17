import os
from models import VideoJob


import subprocess

def generate_thumbnail(video_path, job_dir):
    thumb_path = os.path.join(job_dir, "thumbnail.jpg")
    print("VIDEO:", video_path, type(video_path))
    print("DIR:", job_dir, type(job_dir))

    subprocess.run([
    "ffmpeg",
    "-y",
    "-ss", "00:00:02",
    "-i", video_path,
    "-vframes", "1",
    "-q:v", "2",
    thumb_path
])

    return thumb_path

def get_user_jobs_with_outputs(user_id):
    jobs = VideoJob.query.filter_by(user_id=user_id).order_by(VideoJob.id.desc()).all()

    results = []

    for job in jobs:
        clips_dir = os.path.join(job.job_dir, "clips") if job.job_dir else None

        clips = []
        if clips_dir and os.path.exists(clips_dir):
            clips = [
                f for f in os.listdir(clips_dir)
                if f.endswith(".mp4")
            ]

        results.append({
            "job": job,
            "clips": clips,
            "autosub": job.output_file
        })

    return results

