import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URL = os.environ.get("MONGO_URL")

CHANNEL_ID = -1003801817080
GROUP_ID = -1003836121942

bot = Client(
    "moviebot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# start
@bot.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text(
        "👋 Welcome to MOVIE UNIVERSE FILE PROVIDER\n\nSend movie name."
    )

# group search
@bot.on_message(filters.text & filters.chat(GROUP_ID))
async def search_group(client, message):
    query = message.text

    await message.reply_text("🔎 Searching...")

    results = []
    async for msg in client.search_messages(CHANNEL_ID, query, limit=10):
        if msg.document or msg.video:
            file_id = msg.id
            name = msg.document.file_name if msg.document else msg.video.file_name

            btn = InlineKeyboardMarkup([
                [InlineKeyboardButton("📥 Get File", url=f"https://t.me/{bot.me.username}?start={file_id}")]
            ])

            await message.reply_text(
                f"🎬 {name}",
                reply_markup=btn
            )

# dm open
@bot.on_message(filters.command("start") & filters.private)
async def send_file(client, message):
    if len(message.command) == 1:
        return

    file_id = int(message.command[1])

    msg = await client.get_messages(CHANNEL_ID, file_id)
    sent = await msg.copy(message.chat.id)

    await message.reply_text(
        "⚠️ File will delete in 5 minutes"
    )

    await asyncio.sleep(300)
    await sent.delete()

bot.run()
