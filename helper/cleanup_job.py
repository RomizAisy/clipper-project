from datetime import datetime, timezone, timedelta
import os
import shutil
from models import VideoJob
from extensions import db

def cleanup_old_jobs(days=5):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    old_jobs = VideoJob.query.filter(
        VideoJob.created_at < cutoff,
        VideoJob.status != "processing"
    ).all()

    for job in old_jobs:
        if job.job_dir and os.path.exists(job.job_dir):
            shutil.rmtree(job.job_dir, ignore_errors=True)

        db.session.delete(job)

    db.session.commit()