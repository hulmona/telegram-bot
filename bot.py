import os
import asyncio
import threading
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient

# ---------------- WEB ----------------
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot running"

def run_web():
    app.run(host="0.0.0.0", port=10000)

# ---------------- ENV ----------------
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

DATABASE_URI = os.environ.get("DATABASE_URI")
DATABASE_NAME = os.environ.get("DATABASE_NAME")

BIN_CHANNEL = int(os.environ.get("BIN_CHANNEL"))
GROUP_ID = int(os.environ.get("GROUP_ID"))

bot = Client("moviebot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

mongo = AsyncIOMotorClient(DATABASE_URI)
db = mongo[DATABASE_NAME]

# ---------------- START DM ----------------
@bot.on_message(filters.command("start") & filters.private)
async def start(client, message):

    if len(message.command) == 1:
        await message.reply_text("Send movie name in group")
        return

    file_id = int(message.command[1])

    msg = await client.get_messages(BIN_CHANNEL, file_id)
    sent = await msg.copy(message.chat.id)

    warn = await message.reply_text("File delete in 5 min")

    await asyncio.sleep(300)
    await sent.delete()
    await warn.delete()

# ---------------- GROUP SEARCH ----------------
@bot.on_message(filters.text & filters.chat(GROUP_ID))
async def search(client, message):

    query = message.text
    wait = await message.reply_text("Searching...")

    bot_info = await client.get_me()

    async for msg in client.search_messages(BIN_CHANNEL, query, limit=10):
        if msg.document or msg.video:

            name = msg.document.file_name if msg.document else msg.video.file_name
            file_id = msg.id

            btn = InlineKeyboardMarkup(
                [[InlineKeyboardButton("Get File",
                url=f"https://t.me/{bot_info.username}?start={file_id}")]]
            )

            await message.reply_text(name, reply_markup=btn)

    await wait.delete()

# ---------------- RUN ----------------
def run_bot():
    bot.run()

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    run_bot()
