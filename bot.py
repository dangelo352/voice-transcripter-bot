#!/usr/bin/env python3
"""
Discord Voice Transcripter Bot
Transcribes voice messages using whisper.cpp and responds with text.
"""
import os
import tempfile
import subprocess
import discord
from discord.ext import commands
from discord.ui import Button, View
import sys
import json
import traceback
import shutil
from datetime import datetime

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
WHISPER_MODEL = os.path.expanduser("~/video-dub-pipeline/models/ggml-medium.en.bin")
# Fall back to small if medium not downloaded yet
if not os.path.exists(WHISPER_MODEL):
    WHISPER_MODEL = os.path.expanduser("~/video-dub-pipeline/models/ggml-small.bin")
WHISPER_BIN = "/opt/homebrew/bin/whisper-cli"
LOG_FILE = os.path.join(os.path.dirname(__file__), "bot.log")


def log(msg):
    """Append timestamped message to log file AND print to stdout."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


class TrashView(View):
    """View with a trash button that deletes the transcript and original voice message."""

    def __init__(self, original_message, *, timeout=300):
        super().__init__(timeout=timeout)
        self.original_message = original_message

    @discord.ui.button(emoji="🗑️", style=discord.ButtonStyle.secondary, custom_id="trash_transcript")
    async def trash_callback(self, interaction: discord.Interaction, button: Button):
        # Only the original voice message author can trash
        if interaction.user != self.original_message.author:
            await interaction.response.send_message("Only the person who sent the voice message can delete this.", ephemeral=True)
            return

        # Acknowledge immediately
        await interaction.response.defer(ephemeral=True)

        # Delete the original voice message (might fail without manage_messages)
        try:
            await self.original_message.delete()
        except discord.Forbidden:
            log("⚠️ Can't delete original (no Manage Messages permission)")
        except discord.NotFound:
            pass  # Already deleted

        # Delete the transcript reply (bot's own message - always works)
        try:
            await interaction.message.delete()
        except Exception as e:
            log(f"⚠️ Could not delete transcript: {e}")

        log(f"🗑️ Trashed voice message from {interaction.user}")


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    log(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    log("📡 Listening for voice messages...")


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    log(f"📨 Message from {message.author} in {message.channel} (type={message.channel.type})")
    log(f"   Attachments: {len(message.attachments)}")
    for a in message.attachments:
        log(f"   - {a.filename} | content_type={a.content_type} | size={a.size}")
        if hasattr(a, "flags") and a.flags:
            log(f"     flags.is_voice_message={a.flags.is_voice_message}")

    # Check for voice message attachments - any audio attachment
    for attachment in message.attachments:
        ct = (attachment.content_type or "").lower()
        is_voice = (
            ct.startswith("audio/")
            or attachment.filename.lower().endswith((".ogg", ".mp3", ".wav", ".m4a"))
            or (hasattr(attachment, "flags") and attachment.flags is not None
                and getattr(attachment.flags, "is_voice_message", False))
        )
        log(f"   -> is_voice={is_voice} (ct={ct}, filename={attachment.filename})")
        if is_voice:
            async with message.channel.typing():
                await transcribe_and_reply(message, attachment)
            return

    await bot.process_commands(message)


async def transcribe_and_reply(message, attachment):
    """Download voice message, transcribe with whisper.cpp, reply with text."""
    tmp_dir = tempfile.mkdtemp()
    audio_path = os.path.join(tmp_dir, "voice.ogg")
    wav_path = os.path.join(tmp_dir, "voice.wav")

    try:
        # 1. Download the voice message
        log(f"⬇️ Downloading attachment (size={attachment.size})...")
        await attachment.save(audio_path)
        file_size = os.path.getsize(audio_path)
        log(f"✅ Downloaded {file_size} bytes to {audio_path}")

        # 2. Check it's a real audio file
        file_result = subprocess.run(["file", audio_path], capture_output=True, text=True)
        log(f"📁 file command: {file_result.stdout.strip()}")

        # 3. Check ffmpeg can parse it
        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            capture_output=True, text=True
        )
        duration_str = probe.stdout.strip()
        log(f"⏱️  Duration from ffprobe: {duration_str} seconds")

        # 4. Convert to 16kHz mono WAV using ffmpeg
        log("🔄 Converting to 16kHz mono WAV...")
        convert = subprocess.run([
            "ffmpeg", "-y", "-i", audio_path,
            "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            wav_path
        ], capture_output=True, text=True)

        if convert.returncode != 0:
            log(f"❌ ffmpeg error: {convert.stderr[:500]}")
            await message.reply(f"❌ Audio conversion failed: {convert.stderr[:200]}")
            return
        log(f"✅ WAV created: {os.path.getsize(wav_path)} bytes")

        # 5. Verify whisper binary exists
        if not os.path.exists(WHISPER_BIN):
            log(f"❌ whisper-cli not found at {WHISPER_BIN}")
            await message.reply("❌ whisper-cli binary missing on server")
            return
        if not os.path.exists(WHISPER_MODEL):
            log(f"❌ Model not found at {WHISPER_MODEL}")
            await message.reply("❌ Whisper model missing on server")
            return

        # 6. Transcribe with whisper.cpp
        log("🎤 Transcribing with whisper.cpp...")
        # Use 8 threads on M4, explicit English, relaxed thresholds for accuracy
        is_en_model = "en." in os.path.basename(WHISPER_MODEL)
        result = subprocess.run([
            WHISPER_BIN, "-m", WHISPER_MODEL,
            "-f", wav_path,
            "-t", "8",
            "-l", "en" if is_en_model else "auto",
            "-nth", "0.30",      # lower no-speech threshold (default 0.60)
            "-lpt", "-0.50",     # less strict logprob threshold
            "-et", "3.00",       # more permissive entropy threshold
            "-sow",              # split on word for cleaner output
            "-oj",
            "-of", os.path.join(tmp_dir, "out"),
        ], capture_output=True, text=True, timeout=120)

        log(f"whisper exit code: {result.returncode}")
        if result.stderr:
            log(f"whisper stderr (first 300): {result.stderr[:300]}")

        if result.returncode != 0:
            err = result.stderr[:500] if result.stderr else f"exit code {result.returncode}"
            await message.reply(f"❌ Whisper error: {err}")
            return

        # 7. Parse transcript
        json_path = os.path.join(tmp_dir, "out.json")
        text = ""
        if os.path.exists(json_path):
            with open(json_path, "r") as f:
                raw = f.read()
            log(f"📄 JSON output size: {len(raw)} chars")
            data = json.loads(raw)
            # whisper-cli -oj output uses "transcription" array, not flat "text"
            transcription = data.get("transcription", [])
            seg_count = len(transcription)
            if transcription:
                texts = [seg.get("text", "").strip() for seg in transcription]
                text = " ".join(t for t in texts if t)
            else:
                # Fallback for other whisper formats
                text = data.get("text", "").strip()
            log(f"📝 Transcribed: {len(text)} chars, {seg_count} segs")
        else:
            log(f"❌ No out.json found at {json_path}")
            files = os.listdir(tmp_dir)
            log(f"   Files in tmpdir: {files}")

        # 8. Reply with transcript + trash button
        if text:
            view = TrashView(message)
            await message.reply(f"📝 **Transcript:**\n{text}", view=view)
            log("✅ Reply sent!")
        else:
            await message.reply("🤷 Couldn't transcribe that voice message — it might be silent or unclear.")
            log("⚠️  No text in transcript (silent or unclear)")

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr[:500] if e.stderr else str(e)
        log(f"❌ CalledProcessError: {error_msg}")
        await message.reply(f"❌ Transcription error: {error_msg}")
    except Exception as e:
        error_detail = traceback.format_exc()
        log(f"❌ Exception: {error_detail}")
        await message.reply(f"❌ Error: {str(e)[:300]}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@bot.command(name="ping")
async def ping(ctx):
    await ctx.send("pong!")
    log("🏓 Pinged!")


# Run
if __name__ == "__main__":
    if not TOKEN or TOKEN == "PASTE_YOUR_TOKEN_HERE":
        print("❌ Set DISCORD_BOT_TOKEN env var")
        sys.exit(1)
    open(LOG_FILE, "w").close()
    log("🚀 Bot starting...")
    bot.run(TOKEN)
