
from extensions import db
from models import VideoJob
import time
from clipper.tasks.worker_app import get_app

def fake_progress(app, job_id, start, end, duration=60):
    app = get_app()
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
    
