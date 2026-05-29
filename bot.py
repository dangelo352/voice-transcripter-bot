#!/usr/bin/env python3
"""
Discord Voice Transcripter Bot
Transcribes voice messages using faster-whisper and responds with text.
"""
import os
import tempfile
import subprocess
import discord
from discord.ext import commands
from discord.ui import Button, View
from discord import app_commands
import sys
import json
import traceback
import shutil
from datetime import datetime

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")

# faster-whisper config
WHISPER_MODEL_SIZE = os.environ.get("WHISPER_MODEL_SIZE", "medium")
WHISPER_DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")  # cpu or cuda
WHISPER_COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")  # float16, int8_float16, int8

LOG_FILE = os.path.join(os.path.dirname(__file__), "bot.log")

# Import faster-whisper — will be available via requirements.txt
from faster_whisper import WhisperModel

# Initialize model globally (lazy-loaded on first use)
_model = None

def get_model():
    global _model
    if _model is None:
        log(f"🎤 Loading faster-whisper model '{WHISPER_MODEL_SIZE}' on {WHISPER_DEVICE} ({WHISPER_COMPUTE_TYPE})...")
        _model = WhisperModel(
            WHISPER_MODEL_SIZE,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
        )
        log("✅ Whisper model loaded")
    return _model


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
    await bot.tree.sync()
    log(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    log("📡 Listening for voice messages...")
    # Pre-load the model so first transcription is fast
    import asyncio
    asyncio.create_task(_preload_model())


async def _preload_model():
    """Pre-load whisper model in background so first message doesn't lag."""
    log("⏳ Background-loading whisper model...")
    try:
        get_model()
    except Exception as e:
        log(f"⚠️ Model preload failed (will load on demand): {e}")


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

    # Check for voice message attachments
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
    """Download voice message, transcribe with faster-whisper, reply with text."""
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

        # 5. Transcribe with faster-whisper
        log("🎤 Transcribing with faster-whisper...")
        model = get_model()

        # Run in threadpool to avoid blocking the event loop
        import asyncio
        loop = asyncio.get_event_loop()

        def do_transcribe():
            segments, info = model.transcribe(
                wav_path,
                language="en",
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(
                    threshold=0.5,
                    min_speech_duration_ms=500,
                    min_silence_duration_ms=300,
                ),
            )
            text_parts = []
            for seg in segments:
                text_parts.append(seg.text.strip())
            return " ".join(text_parts)

        text = await loop.run_in_executor(None, do_transcribe)
        log(f"📝 Transcribed: {len(text)} chars")

        # 6. Reply with transcript + trash button
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


@bot.hybrid_command(name="ping", description="Check if the bot is alive")
async def ping(ctx):
    await ctx.send("pong!")
    log("🏓 Pinged!")


@bot.hybrid_command(name="dlvoice", description="Download a voice message file from a Discord message link")
@app_commands.describe(link="Full Discord message link (right-click message → Copy Message Link)")
async def dlvoice(ctx, link: str):
    """Download a voice message file from a Discord message link.
    Usage: !dlvoice https://discord.com/channels/@me/channel_id/message_id
    """
    log(f"📥 dlvoice requested by {ctx.author}: {link}")

    # Parse Discord message link
    try:
        parts = link.strip().split("/")
        message_id = int(parts[-1])
        channel_id = int(parts[-2])
    except (ValueError, IndexError):
        await ctx.reply("❌ Invalid Discord message link. Format: `https://discord.com/channels/.../.../message_id`")
        return

    # Fetch the channel
    channel = bot.get_channel(channel_id)
    if channel is None:
        log(f"   Channel {channel_id} not in cache, trying to fetch...")
        try:
            channel = await bot.fetch_channel(channel_id)
        except Exception as e:
            log(f"   Failed to fetch channel: {e}")
            await ctx.reply("❌ Couldn't find that channel. Is the bot in that server/DM?")
            return

    # Fetch the message
    try:
        msg = await channel.fetch_message(message_id)
    except discord.Forbidden:
        await ctx.reply("❌ Bot doesn't have permission to read messages in that channel.")
        return
    except discord.NotFound:
        await ctx.reply("❌ Message not found — link may be wrong or message was deleted.")
        return
    except Exception as e:
        log(f"   Fetch error: {e}")
        await ctx.reply(f"❌ Error fetching message: {e}")
        return

    log(f"   Fetched message from {msg.author}, {len(msg.attachments)} attachments")

    # Find the first voice/audio attachment
    voice_att = None
    for att in msg.attachments:
        ct = (att.content_type or "").lower()
        if ct.startswith("audio/") or att.filename.lower().endswith((".ogg", ".mp3", ".wav", ".m4a")):
            voice_att = att
            break

    if voice_att is None:
        await ctx.reply("❌ No voice/audio attachment found in that message.")
        return

    # Download and send
    tmp_path = tempfile.mktemp(suffix=f"-{voice_att.filename}")
    try:
        await voice_att.save(tmp_path)
        file_size = os.path.getsize(tmp_path)
        log(f"   Downloaded {file_size} bytes, sending...")
        await ctx.reply(
            f"🎤 Voice message from **{msg.author}** ({file_size / 1024:.0f} KB):",
            file=discord.File(tmp_path, filename=voice_att.filename)
        )
        log("✅ Voice file sent!")
    except Exception as e:
        log(f"   Download/send error: {e}")
        await ctx.reply(f"❌ Error: {e}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# Run
if __name__ == "__main__":
    if not TOKEN or TOKEN == "PASTE_YOUR_TOKEN_HERE":
        print("❌ Set DISCORD_BOT_TOKEN env var")
        sys.exit(1)
    open(LOG_FILE, "w").close()
    log("🚀 Bot starting...")
    bot.run(TOKEN)