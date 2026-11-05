FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for Playwright and network tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir -e . httpx supabase duckduckgo_search maigret sherlock-project uvicorn

COPY . .

EXPOSE 8000

CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
