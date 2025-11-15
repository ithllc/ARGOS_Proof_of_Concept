import os
import redis

# Load environment variables before other imports
import config

class RedisClient:
    def __init__(self):
        """
        Initializes the Redis client, connecting to either a local instance or a Google Cloud Memorystore instance.
        """
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        
        try:
            self.client = redis.Redis(host=redis_host, port=redis_port, db=0, decode_responses=True)
            self.client.ping()
            print("Successfully connected to Redis.")
        except redis.exceptions.ConnectionError as e:
            print(f"Error connecting to Redis: {e}")
            self.client = None

    def get_client(self):
        return self.client

    # Task Queue functions (using Lists)
    def push_task(self, queue_name, task_data):
        if self.client:
            self.client.lpush(queue_name, task_data)

    def pop_task(self, queue_name):
        if self.client:
            return self.client.rpop(queue_name)

    # State management functions (using Hashes)
    def set_hash_field(self, hash_name, field, value):
        if self.client:
            self.client.hset(hash_name, field, value)

    def get_hash_field(self, hash_name, field):
        if self.client:
            return self.client.hget(hash_name, field)

    def get_all_hash_fields(self, hash_name):
        if self.client:
            return self.client.hgetall(hash_name)

    # Results/Cache functions (using Strings with TTL)
    def set_with_ttl(self, key, value, ttl_seconds):
        if self.client:
            self.client.setex(key, ttl_seconds, value)

    def get(self, key):
        if self.client:
            return self.client.get(key)

    # Pub/Sub functions
    def publish_message(self, channel, message):
        if self.client:
            self.client.publish(channel, message)

    def subscribe_to_channel(self, channel):
        if self.client:
            pubsub = self.client.pubsub()
            pubsub.subscribe(channel)
            return pubsub

redis_client = RedisClient()
