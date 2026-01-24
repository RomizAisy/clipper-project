import os
from models import VideoJob

def get_user_jobs_with_clips(user_id):
    jobs = (
        VideoJob.query
        .filter_by(user_id=user_id)
        .order_by(VideoJob.id.desc())
        .all()
    )

    result = []

    for job in jobs:
        clips_dir = os.path.join(job.job_dir, "clips")
        clips = []

        if os.path.exists(clips_dir):
            clips = sorted(
                f for f in os.listdir(clips_dir)
                if f.endswith(".mp4")
            )

        result.append({
            "job": job,
            "clips": clips
        })

    return result
