# Voice Transcripter Bot 🎤

A Discord bot that transcribes voice messages using **faster-whisper**. Fast, local, private — runs on Railway or your own machine.

## Features

- **Auto-transcribe** — any voice message in any channel/server gets transcribed instantly
- **Trash button** 🗑️ — click to delete both the voice message and the transcript (owner-only)
- **faster-whisper** — optimized CPU inference with CTranslate2, no GPU required
- **Auto-restart** — if the bot crashes, it comes back (Railway handles this automatically)
- **Detailed logging** — every step logged to stdout and `bot.log`

## Deploy on Railway (recommended)

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/dangelo352/voice-transcripter-bot)

Or via the CLI:

```bash
railway login
railway init
railway deploy
```

Then set your environment variable:

```
DISCORD_BOT_TOKEN=your_bot_token_here
```

### Deploy Options

| Variable | Default | Description |
|----------|---------|-------------|
| `DISCORD_BOT_TOKEN` | (required) | Your Discord bot token |
| `WHISPER_MODEL_SIZE` | `medium` | Model size: tiny, base, small, medium, large-v3 |
| `WHISPER_DEVICE` | `cpu` | Device: cpu or cuda |
| `WHISPER_COMPUTE_TYPE` | `int8` | Compute: int8, int8_float16, float16 |

## Local Setup

```bash
# Clone
git clone https://github.com/dangelo352/voice-transcripter-bot
cd voice-transcripter-bot

# Virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your Discord bot token

# Run
python bot.py
```

Requirements: Python 3.9+, ffmpeg (brew install ffmpeg)

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
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — speech-to-text (CTranslate2)
- ffmpeg — audio conversion
- Python 3