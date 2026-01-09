docker run -d --name XXXX -p 6379:6379 redis redis-server --requirepass "XXXX"

uvicorn main:app --reload
