import asyncio
import threading
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient

# ------------------ WEB SERVER ------------------
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

def run_web():
    app.run(host="0.0.0.0", port=10000)

# ------------------ BOT CONFIG ------------------
API_ID = 38438389
API_HASH = "327b2592682ff56d760110350e66425e"
BOT_TOKEN = "PASTE_REAL_TOKEN"

DATABASE_URI = "PASTE_REAL_MONGO_URI"
DATABASE_NAME = "autofilter"

ADMINS = [7916138581]
BIN_CHANNEL = -1003801817080
GROUP_ID = -1003836121942

bot = Client("moviebot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

mongo = AsyncIOMotorClient(DATABASE_URI)
db = mongo[DATABASE_NAME]
users_col = db.users


async def save_user(user_id):
    if not await users_col.find_one({"_id": user_id}):
        await users_col.insert_one({"_id": user_id})


@bot.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await save_user(message.from_user.id)

    if len(message.command) == 1:
        await message.reply_text("👋 Welcome to Movie Bot\n\nSearch movie in group.")
        return

    try:
        file_id = int(message.command[1])
    except:
        await message.reply_text("Invalid link")
        return

    msg = await client.get_messages(BIN_CHANNEL, file_id)
    sent = await msg.copy(message.chat.id)

    warn = await message.reply_text("⚠️ File will delete in 5 minutes")
    await asyncio.sleep(300)

    try:
        await sent.delete()
        await warn.delete()
    except:
        pass


@bot.on_message(filters.text & filters.chat(GROUP_ID))
async def search(client, message):
    query = message.text
    wait = await message.reply_text("🔎 Searching...")

    found = False
    bot_info = await client.get_me()

    async for msg in client.search_messages(BIN_CHANNEL, query, limit=10):
        if msg.document or msg.video:
            found = True
            name = msg.document.file_name if msg.document else msg.video.file_name
            file_id = msg.id

            btn = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "📥 Get File",
                    url=f"https://t.me/{bot_info.username}?start={file_id}"
                )]
            ])

            await message.reply_text(f"🎬 {name}", reply_markup=btn)

    await wait.delete()

    if not found:
        await message.reply_text("❌ Movie not found")


def run_bot():
    bot.run()


# ------------------ MAIN ------------------
if __name__ == "__main__":
    t1 = threading.Thread(target=run_web)
    t1.start()

    run_bot()
