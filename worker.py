from rq.worker import SimpleWorker   # ✅ change this
from extensions import redis_conn
from app import create_app

app = create_app()

with app.app_context():
    worker = SimpleWorker(["clipper"], connection=redis_conn)
    worker.work()