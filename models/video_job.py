from extensions import db
from datetime import datetime, timezone

class VideoJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    status = db.Column(db.String(50))   # pending, processing, done, failed
    progress = db.Column(db.Integer)    # 0–100
    step = db.Column(db.String(50))     # upload, transcribe, nlp, cutting
    job_dir = db.Column(db.String(255))
    created_at = db.Column(db.DateTime(timezone=True),default=lambda: datetime.now(timezone.utc)
)
    result = db.Column(db.JSON)