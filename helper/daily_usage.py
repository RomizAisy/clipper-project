from .plans import PLANS
from datetime import date
from models import VideoJob



def can_start_job(user):
    today = date.today()

    # reset daily usage
    if user.last_reset != today:
        user.used_today = 0
        user.last_reset = today

    running = VideoJob.query.filter(
        VideoJob.user_id == user.id,
        VideoJob.status == "processing"
    ).count()

    if user.daily_limit != -1 and (user.used_today + running) >= user.daily_limit:
        return False

    return True