# Swappy Bot

Swappy Bot is a bot based on the OKX dex api that allows you to perform trading operations on EVM networks such as:

## Features
- Swap
- Limit order
- Crosschain(EVM only)
- Withdraw from wallet

## Installation

1. Clone the repository:
   ```sh
   git clone https://github.com/hrosablock/swappy.git
   cd swappy
   ```
2. Configure environment variables:
   - Copy `.env.example` to `.env` and update the necessary values.
   - Edit `bot_name` in `bot/config.py`

3. Build and start the container:
   ```sh
   docker-compose up --build
   ```

## Usage

The bot will start running automatically after executing the above command.
