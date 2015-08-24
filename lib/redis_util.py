import redis
import os

redis_shell = redis.from_url(os.getenv('REDIS_URL'))
