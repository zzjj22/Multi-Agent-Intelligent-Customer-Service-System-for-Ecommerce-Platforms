docker run -d --name my-redis -p 6379:6379 redis redis-server --requirepass "hz030415"
redis-cli -h 127.0.0.1 -p 6378 ping

uvicorn main:app --reload
