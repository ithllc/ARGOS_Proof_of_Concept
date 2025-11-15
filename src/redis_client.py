import os
import redis

# Load environment variables before other imports
import config

class RedisClient:
    def __init__(self):
        """
        Initializes the Redis client, connecting to either a local instance or a cloud-based instance (e.g., Google Cloud Memorystore).
        
        The following environment variables are used for configuration:
        - REDIS_HOST: The hostname of the Redis server (default: 'localhost').
        - REDIS_PORT: The port of the Redis server (default: 6379).
        - REDIS_PASSWORD: The password for the Redis server (optional).
        - REDIS_SSL: Set to 'true' to enable SSL/TLS (e.g., for cloud connections).
        """
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_password = os.getenv("REDIS_PASSWORD", None)
        redis_ssl = os.getenv("REDIS_SSL", "false").lower() == 'true'

        connection_kwargs = {
            "host": redis_host,
            "port": redis_port,
            "password": redis_password,
            "decode_responses": True
        }

        if redis_ssl:
            connection_kwargs["ssl"] = True
            connection_kwargs["ssl_cert_reqs"] = None

        try:
            self.client = redis.Redis(**connection_kwargs)
            self.client.ping()
            print(f"Successfully connected to Redis at {redis_host}:{redis_port}.")
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
