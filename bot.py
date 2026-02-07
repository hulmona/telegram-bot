import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

CHANNEL_ID = int(os.environ.get("CHANNEL_ID"))
GROUP_ID = int(os.environ.get("GROUP_ID"))

bot = Client(
    "moviebot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# START MESSAGE DM
@bot.on_message(filters.command("start") & filters.private)
async def start_dm(client, message):
    if len(message.command) == 1:
        await message.reply_text(
            "👋 Welcome to MOVIE UNIVERSE FILE PROVIDER\n\nSend movie name in group."
        )
        return

    file_id = int(message.command[1])
    msg = await client.get_messages(CHANNEL_ID, file_id)

    sent = await msg.copy(message.chat.id)

    warn = await message.reply_text(
        "⚠️ File will delete in 5 minutes\nForward and download fast."
    )

    await asyncio.sleep(300)
    await sent.delete()
    await warn.delete()


# GROUP SEARCH
@bot.on_message(filters.text & filters.chat(GROUP_ID))
async def search_group(client, message):
    query = message.text

    searching = await message.reply_text("🔎 Searching...")

    found = False

    async for msg in client.search_messages(CHANNEL_ID, query, limit=20):
        if msg.document or msg.video:

            file_id = msg.id
            name = msg.document.file_name if msg.document else msg.video.file_name

            btn = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "📥 Get File",
                    url=f"https://t.me/{(await bot.get_me()).username}?start={file_id}"
                )]
            ])

            await message.reply_text(
                f"🎬 {name}",
                reply_markup=btn
            )
            found = True

    await searching.delete()

    if not found:
        await message.reply_text("❌ Not found")


bot.run()
