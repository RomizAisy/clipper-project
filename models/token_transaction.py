from datetime import datetime
from extensions import db

class TokenTransaction(db.Model):
    __tablename__ = "token_transactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    amount = db.Column(db.Integer, nullable=False)  # negative = used, positive = added
    description = db.Column(db.String(255))
    created_at = db.Column(
        db.DateTime,
        default=db.func.now()
    )