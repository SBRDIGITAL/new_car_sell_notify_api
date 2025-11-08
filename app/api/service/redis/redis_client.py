from redis.asyncio.client import Redis

from app.config.config_reader import env_config



# Для dev окружения параметры берутся из env_config (см. .env.template)
redis_client = Redis(
	host=env_config.redis_host,
	port=env_config.redis_port,
	db=env_config.redis_db,
	decode_responses=True,
)
# Пример использования:
# await redis_client.xadd("new_car_notify_stream", {"data": json.dumps(payload)})