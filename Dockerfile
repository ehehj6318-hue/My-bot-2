FROM mcr.microsoft.com/playwright:v1.48.0-jammy

WORKDIR /app

# Dependencies copy karo
COPY requirements.txt .
RUN pip install -r requirements.txt

# Playwright browser install karo (Chromium)
RUN playwright install chromium

# Code copy karo
COPY . .

# Bot chalao
CMD ["python", "bot.py"]
