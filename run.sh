#!/bin/bash
cd "$(dirname "$0")"
source .env
while true; do
    echo "[$(date)] Starting bot..."
    python3 bot.py
    echo "[$(date)] Bot exited (code $?). Restarting in 3s..."
    sleep 3
done
