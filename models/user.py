from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from datetime import datetime, timedelta
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

    subscription_start = db.Column(
    db.Date,
    nullable=False,
    default=lambda: datetime.utcnow().date()
    )

    used_this_cycle = db.Column(db.Integer, default=0)

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

    def reset_subscription_if_needed(self):
        """Reset monthly usage every 30 days (for paid users only)."""
        plan_info = PLANS.get(self.plan, {})

        if plan_info.get("is_free"):
            return

        today = datetime.utcnow().date()

        if today >= self.subscription_start + timedelta(days=30):
            self.used_this_cycle = 0
            self.subscription_start = today
            db.session.commit()

    def remaining_quota(self):
        plan_info = PLANS.get(self.plan, {})

        if plan_info.get("is_free") and self.last_reset != datetime.utcnow().date():
            self.used_today = 0
            self.last_reset = datetime.utcnow().date()

        else:
            # Paid → monthly system
            self.reset_subscription_if_needed()
            return max(0, plan_info["monthly_limit"] - self.used_this_cycle)
        
    def consume_quota(self, amount=1):
        plan_info = PLANS.get(self.plan, {})

        if plan_info.get("is_free"):
            self.used_today += amount
        else:
            self.reset_subscription_if_needed()
            self.used_this_cycle += amount

        db.session.commit()