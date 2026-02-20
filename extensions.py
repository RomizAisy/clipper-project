from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail
import redis
from rq import Queue

db = SQLAlchemy()
migrate = Migrate()
mail = Mail()


# ---------------- REDIS QUEUE ----------------
redis_conn = redis.Redis(
    host="localhost",
    port=6379,
    db=0
)

clipper_queue = Queue(
    "clipper",
    connection=redis_conn,
    default_timeout=7200  # long video jobs
)