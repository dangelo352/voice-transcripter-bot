#!/usr/bin/env python3
"""Minimal bot for Railway deployment test."""
import os, sys, discord
from discord.ext import commands

TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
if not TOKEN:
    print("DISCORD_BOT_TOKEN not set")
    sys.exit(1)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

@bot.hybrid_command(name="ping", description="Check bot status")
async def ping(ctx):
    await ctx.send("pong!")

print("Starting bot...")
bot.run(TOKEN)
