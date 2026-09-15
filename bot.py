# Bill Cypher Chk — Kaori-style safe sandbox

A structured Telegram bot with:
- Welcome panel
- Optional GIF welcome
- Command Center
- Sandbox analyzer with automatic progress
- Gateway and Tools pages
- Account / Credits / Premium
- Owner Diamond console
- SQLite persistence
- Render-compatible Flask + polling

## Render environment variables

Required:
- BOT_TOKEN = your private BotFather token
- ADMIN_ID = your Telegram numeric user ID

Optional:
- WELCOME_GIF_FILE_ID = Telegram file_id of your GIF
- PORT = 10000

## GIF

You can simply send a GIF/animation to the bot from the owner account.
The bot will capture its Telegram file_id and use it for `/start` during
the current process. For persistence after Render restarts, put that file_id
into WELCOME_GIF_FILE_ID.

## Safety

The checker is intentionally a sandbox simulation. It does not:
- process real cards
- query CVV
- check funds
- authorize payment cards
- connect to live payment gateways

The "Gateways" page contains UI/status simulation modules only.
