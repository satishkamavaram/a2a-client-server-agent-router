import redis
import os
from typing import Optional
from redisvl.extensions.cache.llm import SemanticCache
from redisvl.utils.vectorize import OpenAITextVectorizer
from redisvl.extensions.cache.embeddings import EmbeddingsCache
from dotenv import load_dotenv

load_dotenv()

# cache in redis
# [{'entry_id': '2990b8f25d9f7a585798544a7231ffcec5f0ef7507691f077cf70ba889af83ee', 'prompt': 'What is Java?', 'response': 'Java is a programming language', 'vector_distance': 0.246054828167,
#    'inserted_at': 1763994769.61, 'updated_at': 1763994769.61, 'metadata': {'key1': 'value1', 'key2': 'value2'}, 'key': 'llm-cache:2990b8f25d9f7a585798544a7231ffcec5f0ef7507691f077cf70ba889af83ee'}]


class RedisCache:
    def __init__(self):
        self.redis_enabled = os.getenv(
            'REDIS_ENABLED', 'false').lower() == 'true'
        self.cache = None
        print("Redis cache is enabled!!!")
        if self.redis_enabled:
            self._initialize_redis()

    def _initialize_redis(self):
        try:
            redis_client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                password=os.getenv('REDIS_PASSWORD', 'redispass123'),
                db=int(os.getenv('REDIS_DB', 0)),
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )

            # Test connection
            redis_client.ping()
            print("✅ Redis connected successfully")

            # Initialize vectorizer and cache
            vectorizer = OpenAITextVectorizer(
                model="text-embedding-3-small",
                cache=EmbeddingsCache(redis_client=redis_client, ttl=3600)
            )

            self.cache = SemanticCache(
                name="llm-cache",
                vectorizer=vectorizer,
                redis_client=redis_client,
                distance_threshold=0.5
            )

        except Exception as e:
            print(f"Redis initialization failed: {e}")
            self.redis_enabled = False

    def store(self, user_question: str, llm_answer: str, ttl: int = 3600):
        if not self.redis_enabled or not self.cache:
            return

        try:
            self.cache.set_ttl(ttl)
            self.cache.store(prompt=user_question, response=llm_answer,  metadata={
                             "key1": "value1", "key2": "value2"})
        except Exception as e:
            print(f"Failed to store in cache: {e}")

    def get_from_cache(self, user_question: str, distance_threshold: float = 0.2):
        if not self.redis_enabled or not self.cache:
            return None

        try:
            return self.cache.check(user_question, distance_threshold=distance_threshold)
        except Exception as e:
            print(f"Failed to get from cache: {e}")
            return None


_SINGLETON: Optional[RedisCache] = None


def get_cache(initialize: bool = True) -> RedisCache:
    global _SINGLETON
    if _SINGLETON is None and initialize:
        _SINGLETON = RedisCache()
    return _SINGLETON
