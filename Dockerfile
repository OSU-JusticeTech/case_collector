FROM ghcr.io/astral-sh/uv:debian-slim

RUN apt update && apt install -y libgdal-dev && rm -rf /var/lib/apt/lists/*
# Copy the project into the image
COPY . /app

# Disable development dependencies
ENV UV_NO_DEV=1

# Sync the project into a new environment, asserting the lockfile is up to date
WORKDIR /app
RUN uv sync

CMD ["sh","-c","uv run manage.py collectstatic --noinput && uv run manage.py createcachetable && uv run manage.py migrate && uv run uvicorn eviction_tool.asgi:application --host 0.0.0.0"]

