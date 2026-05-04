#!/bin/bash
cd "$(dirname "$0")"
source .env
while true; do
    echo "[$(date)] Starting bot..."
    ~/.venvs/discord-bot/bin/python bot.py
    echo "[$(date)] Bot exited (code $?). Restarting in 3s..."
    sleep 3
done
