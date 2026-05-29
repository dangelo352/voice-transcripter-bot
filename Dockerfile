FROM python:3.11-slim

# System deps: ffmpeg for audio conversion, git for faster-whisper model downloads
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    file \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY bot.py .
COPY tiktok_lookup.py .
COPY .env.example .env.example

# Railway provides DISCORD_BOT_TOKEN via env var
CMD ["python", "bot.py"]