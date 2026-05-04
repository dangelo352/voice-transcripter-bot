# Voice Transcripter Bot 🎤

A Discord bot that transcribes voice messages using [whisper.cpp](https://github.com/ggerganov/whisper.cpp). Fast, local, private — runs entirely on your machine.

## Features

- **Auto-transcribe** — any voice message in any channel/server gets transcribed instantly
- **Trash button** 🗑️ — click to delete both the voice message and the transcript (owner-only)
- **Local whisper.cpp** — no cloud API, no costs, no data leaving your machine
- **Auto-restart** — if the bot crashes, it comes back in 3 seconds
- **Detailed logging** — every step logged to `bot.log`

## Requirements

- macOS (Apple Silicon) or Linux
- [whisper.cpp](https://github.com/ggerganov/whisper.cpp) installed (`whisper-cli` in PATH)
- A whisper model (`ggml-small.bin`, `ggml-medium.en.bin`, etc.)
- ffmpeg
- Python 3.9+

## Setup

```bash
# Clone or download
cd voice-transcripter-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install discord.py python-dotenv

# Copy and fill in your bot token
cp .env.example .env
# Edit .env with your Discord bot token

# Make sure whisper-cli and a model are available
# e.g. via Homebrew: brew install whisper-cpp
# Download model: curl -LO https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.en.bin

# Run
./run.sh
```

## Config

Edit `bot.py` to change:
- `WHISPER_MODEL` — path to your whisper.cpp model file
- `WHISPER_BIN` — path to `whisper-cli` binary

## Invite to Server

```
https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=11264&integration_type=0&scope=bot
```

Requires **Send Messages** + **Manage Messages** permissions (for the trash button).

## Usage

1. Invite the bot to your server
2. Send a voice message in any channel
3. Bot replies with the transcript automatically
4. Click 🗑️ on the reply to clean up

## Tech Stack

- [discord.py](https://github.com/Rapptz/discord-py) — Discord API
- [whisper.cpp](https://github.com/ggerganov/whisper.cpp) — local speech-to-text
- ffmpeg — audio conversion
- Python 3
