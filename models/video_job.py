from extensions import db
from datetime import datetime, timezone
from sqlalchemy.sql import func

class VideoJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # old
    user_id = db.Column(db.Integer, nullable=True)

    # new
    guest_id = db.Column(
        db.String(64),
        nullable=True,
        index=True
    )

    status = db.Column(db.String(50))
    job_type = db.Column(db.String(20))
    progress = db.Column(db.Integer)
    step = db.Column(db.String(50))
    job_dir = db.Column(db.String(255))
    original_filename = db.Column(db.String(255))
    output_file = db.Column(db.String)
    thumbnail_file = db.Column(db.String(255))

    # keep temporarily
    required_tokens = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    usage_charged = db.Column(
        db.Boolean,
        default=False
    )

    aspect_ratio = db.Column(
        db.String(20),
        default="original"
    )

    clips_data = db.Column(
        db.Text,
        nullable=True
    )

    transcript_data = db.Column(
        db.Text,
        nullable=True
    )

    subtitle_style = db.Column(
        db.String(50),
        default="default_portrait"
    )

    created_at = db.Column(
        db.DateTime,
        default=db.func.now()
    )

    result = db.Column(db.JSON)