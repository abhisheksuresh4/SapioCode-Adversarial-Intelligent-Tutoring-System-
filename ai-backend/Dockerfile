FROM python:3.12-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install production-only dependencies
RUN pip install --no-cache-dir \
    asyncpg \
    sqlalchemy[asyncio] \
    python-jose[cryptography] \
    passlib[bcrypt] \
    redis[hiredis] \
    neo4j

# Copy application code
COPY . .

EXPOSE 8002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
