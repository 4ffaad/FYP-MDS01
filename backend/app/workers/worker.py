"""Run the RQ worker process."""

from redis import Redis
from rq import Queue, Worker

from backend.app.core.config import REDIS_URL, RQ_QUEUE_NAME


if __name__ == "__main__":
    connection = Redis.from_url(REDIS_URL)
    Worker([Queue(RQ_QUEUE_NAME, connection=connection)], connection=connection).work()

