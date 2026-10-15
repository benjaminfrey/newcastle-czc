FROM python:3.14-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY alembic.ini .
COPY migrations ./migrations
COPY portal_api ./portal_api
USER nobody
# Migrate, then serve. --proxy-headers so rate limits see the visitor's IP, not Caddy's.
# --no-access-log: request lines would record what addresses people search for, with their
# IP, indefinitely. Errors are still logged.
CMD ["sh", "-c", "python -m alembic upgrade head && uvicorn portal_api.main:create_app --factory --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips '*' --no-access-log"]
