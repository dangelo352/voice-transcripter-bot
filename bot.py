#!/usr/bin/env python3
"""Discord Bot with TikTok lookup and Fameswap OCR scanning."""
import os, sys, json, traceback, tempfile, subprocess, shutil, re, base64
from datetime import datetime
import discord
from discord.ext import commands
from discord.ui import Button, View
from discord import app_commands
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
LOG_FILE = os.path.join(os.path.dirname(__file__), "bot.log")

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    log(f"Logged in as {bot.user} (ID: {bot.user.id})")

# --- TikTok lookup ---
@bot.hybrid_command(name="tiktok", description="Look up a TikTok profile")
@app_commands.describe(username="TikTok username")
async def tiktok(ctx, username: str):
    log(f"TikTok lookup: {ctx.author}: {username}")
    await ctx.defer()
    try:
        from tiktok_lookup import fetch_tiktok_profile, format_profile, extract_username_from_input
        clean = extract_username_from_input(username)
        if not clean:
            await ctx.reply("Invalid username.")
            return
        data = fetch_tiktok_profile(clean)
        await ctx.reply(format_profile(data) if data else "User not found.")
    except Exception as e:
        traceback.print_exc()
        await ctx.reply(f"Error: {str(e)[:200]}")

# --- Fameswap OCR scan ---
@bot.hybrid_command(name="usa", description="Scan Fameswap screenshots")
async def usa(ctx):
    images = [a for a in ctx.message.attachments if (a.content_type or "").lower().startswith("image/")]
    if not images:
        await ctx.reply("Attach Fameswap screenshot(s).")
        return
    log(f"Fameswap scan: {ctx.author} ({len(images)} images)")
    await ctx.defer()
    from fameswap_ocr import parse_fameswap_image, format_fameswap_results
    from tiktok_lookup import fetch_tiktok_profile
    all_u = set()
    tmp_paths = []
    try:
        for i, img in enumerate(images, 1):
            p = tempfile.mktemp(suffix=f"-{img.filename}")
            tmp_paths.append(p)
            await img.save(p)
            r = parse_fameswap_image(p)
            if not r.get('error'):
                all_u.update(r['usernames'])
        if not all_u:
            await ctx.reply("No usernames found.")
            return
        profiles = []
        for u in sorted(all_u):
            d = fetch_tiktok_profile(u)
            if d: d['username'] = u
            else: d = {'username': u, 'error': 'Not found'}
            profiles.append(d)
        reply = format_fameswap_results(profiles)
        if len(reply) > 1900: reply = reply[:1900] + "\n...truncated"
        await ctx.reply(reply)
    except Exception as e:
        traceback.print_exc()
        await ctx.reply(f"Error: {str(e)[:200]}")
    finally:
        for p in tmp_paths:
            if os.path.exists(p): os.remove(p)

@bot.hybrid_command(name="ping", description="Check bot status")
async def ping(ctx):
    await ctx.send("pong!")
    log("Ping!")

if __name__ == "__main__":
    if not TOKEN:
        print("Set DISCORD_BOT_TOKEN")
        sys.exit(1)
    open(LOG_FILE, "w").close()
    log("Starting...")
    bot.run(TOKEN)
