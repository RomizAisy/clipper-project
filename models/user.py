from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from datetime import datetime



#DATABASE USER MODEL
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(40), unique = True, nullable = False)
    email = db.Column(db.String(100), unique = True, nullable = False)
    password_hash = db.Column(db.String(200), nullable = False)
    tokens = db.Column(db.Integer, default = 0)
    is_verified = db.Column(db.Boolean, default=False)
    plan = db.Column(db.String(20), default="free")
    used_today = db.Column(db.Integer, default=0)
    last_reset = db.Column(db.Date, default=lambda: datetime.utcnow().date())

    # daily quota limit (copied from PLANS at purchase)
    daily_limit = db.Column(
        db.Integer,
        default=2   # free plan limit
    )

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'{self.username}'

    def is_unlimited(self):
        return self.daily_limit == -1

    def remaining_quota(self):
        if self.daily_limit == -1:
            return float("inf")
        return max(0, self.daily_limit - self.used_today)
