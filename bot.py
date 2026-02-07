import os
import threading
from flask import Flask
from pyrogram import Client, filters

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID"))

bot = Client(
    "bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# start command
@bot.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("Bot is working ✅")

# search message
@bot.on_message(filters.text & filters.private)
async def search(client, message):
    query = message.text
    await message.reply_text(f"Searching for: {query}")

# web server for render
app = Flask('')

@app.route('/')
def home():
    return "Bot running"

def run():
    app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run).start()

bot.run()
