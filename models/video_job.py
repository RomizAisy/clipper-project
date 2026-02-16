from extensions import db
from datetime import datetime, timezone
from sqlalchemy.sql import func

class VideoJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    status = db.Column(db.String(50))   # pending, processing, done, failed
    job_type = db.Column(db.String(20))  # "clipper" | "autosubs"
    progress = db.Column(db.Integer)    # 0–100
    step = db.Column(db.String(50))     # upload, transcribe, nlp, cutting
    job_dir = db.Column(db.String(255))
    original_filename=db.Column(db.String(255))
    output_file = db.Column(db.String)
    required_tokens = db.Column(db.Integer, nullable=False, default=0)
    usage_charged = db.Column(db.Boolean, default=False)
    job_type = db.Column(db.String(20))  
    aspect_ratio = db.Column(db.String(20), default="original")
    created_at = db.Column(
        db.DateTime,
        default=db.func.now()
    )

    
    result = db.Column(db.JSON)