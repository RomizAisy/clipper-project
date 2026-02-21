from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from datetime import datetime
from helper.plans import PLANS


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

    free_limit = 3

    # daily quota limit (copied from PLANS at purchase)
    daily_limit = db.Column(
        db.Integer,
        default=3   # free plan limit
    )

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'{self.username}'

    def reset_if_needed(self):
        """Reset used_today only for non-free users."""
        plan_info = PLANS.get(self.plan, {})
        if not plan_info.get("is_free") and self.last_reset != datetime.utcnow().date():
            self.used_today = 0
            self.last_reset = datetime.utcnow().date()
            db.session.commit()

    def remaining_quota(self):
        plan_info = PLANS.get(self.plan, {})
        if plan_info.get("is_free"):
            # Free users never reset daily
            return max(0, plan_info["daily_limit"] - self.used_today)
        else:
            # Paid users: daily limit applies
            self.reset_if_needed()
            return max(0, plan_info["daily_limit"] - self.used_today)