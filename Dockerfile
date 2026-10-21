# Base image with Python 3.12 and Playwright dependencies
FROM mcr.microsoft.com/playwright:v1.48.0-jammy

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies (this will now use Python 3.12)
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium

# Copy the rest of the application
COPY . .

# Command to run the bot
CMD ["python", "bot.py"]
