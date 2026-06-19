FROM python:3.13-slim

# Install uv via pip so builds do not depend on ghcr.io (often blocked on PaaS hosts).
RUN pip install --no-cache-dir uv

# Copy the application into the container.
COPY . /app

# Install the application dependencies.
WORKDIR /app
RUN uv sync --frozen --no-cache

# Run the application.
CMD ["/app/.venv/bin/fastapi", "run", "./main.py", "--port", "80", "--host", "0.0.0.0"]