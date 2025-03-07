FROM python:3.11-slim

WORKDIR /app

# Install minimal system dependencies
RUN apt-get update && apt-get install -y \
    protobuf-compiler \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry && \
    poetry config virtualenvs.create false

# Copy project files
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-interaction --no-ansi --no-root --without dev

# Copy application code
COPY . .

# Security: Create non-root user
RUN useradd -m appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 7860

# CMD ["poetry", "run", "python", "main.py"]
