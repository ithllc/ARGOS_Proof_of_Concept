class MockRedisClient:
    """A mock Redis client for testing purposes."""
    def __init__(self):
        self.queues = {}
        self.hashes = {}
        self.published_messages = {}

    def push_task(self, queue_name, task):
        if queue_name not in self.queues:
            self.queues[queue_name] = []
        self.queues[queue_name].insert(0, task)

    def pop_task(self, queue_name):
        if queue_name in self.queues and self.queues[queue_name]:
            return self.queues[queue_name].pop()
        return None

    def publish_message(self, channel, message):
        self.published_messages[channel] = message

    def get_published_message(self, channel):
        return self.published_messages.get(channel)

    def set_hash_field(self, hash_name, key, value):
        if hash_name not in self.hashes:
            self.hashes[hash_name] = {}
        self.hashes[hash_name][key] = value

    def get_hash_field(self, hash_name, key):
        return self.hashes.get(hash_name, {}).get(key)

    def get_all_hash_fields(self, hash_name):
        return self.hashes.get(hash_name, {})
