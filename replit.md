# Crypto Volume Spike Detection Bot

## Overview
A 24/7 Python automation script that monitors Binance cryptocurrency volume spikes and sends Telegram alerts.

## Features
- Fetches crypto prices and volume data from Binance API every few minutes
- Detects early volume spikes on USDT trading pairs
- Sends alerts to Telegram bot when conditions are met
- Includes Flask keep_alive server on port 8080 for UptimeRobot monitoring

## Project Structure
- `config.py` - Configuration and environment variables
- `binance_client.py` - Binance API client
- `scanner_logic.py` - Volume spike detection algorithm
- `telegram_bot.py` - Telegram alert sender
- `keep_alive.py` - Flask web server for keeping Repl online
- `main.py` - Main loop coordinator
- `requirements.txt` - Python dependencies

## Setup
1. Get a Telegram Bot Token from @BotFather
2. Get your Telegram Chat ID
3. Add these as environment secrets in Replit:
   - TELEGRAM_BOT_TOKEN
   - TELEGRAM_CHAT_ID

## Recent Changes
- 2025-11-13: Initial project structure created

## User Preferences
- User will provide their own implementation code
