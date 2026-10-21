# Python 3.12 use kar rahe hain, 3.14 nahi
FROM python:3.12-slim

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PLAYWRIGHT_BROWSERS_PATH=/app/ms-playwright \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# System dependencies (Playwright Chromium ke liye zaroori)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# Requirements copy karo
COPY requirements.txt .

# Dependencies install karo (ab greenlet compile nahi hoga, wheel milega)
RUN pip install --no-cache-dir -r requirements.txt

# Playwright browser install karo
RUN playwright install chromium

# Baaki code copy karo
COPY . .

# Bot chalao
CMD ["python", "bot.py"]
