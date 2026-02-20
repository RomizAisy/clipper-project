from rq import Queue
from redis_conn import redis_conn

clipper_queue = Queue("clipper", connection=redis_conn)