FROM python:3.12-slim

WORKDIR /app

# Install dependencies before copying source (layer cache)
COPY pyproject.toml .
RUN pip install --no-cache-dir . \
    && pip install --no-cache-dir psycopg2-binary

# Copy source
COPY . .

ENV PYTHONPATH=/app
ENV API_ONLY=true

# Run as non-root
RUN useradd -m appuser
USER appuser

EXPOSE 8080

CMD ["python", "main.py"]
