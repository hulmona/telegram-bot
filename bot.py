import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

CHANNEL_ID = int(os.environ.get("CHANNEL_ID"))
GROUP_ID = int(os.environ.get("GROUP_ID"))

bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@bot.on_message(filters.command("start") & filters.private)
async def start(client, message):
    if len(message.command) == 1:
        await message.reply("Send movie name")
        return

    file_id = int(message.command[1])
    msg = await client.get_messages(CHANNEL_ID, file_id)
    sent = await msg.copy(message.chat.id)

    await asyncio.sleep(300)
    await sent.delete()

@bot.on_message(filters.text & filters.chat(GROUP_ID))
async def search(client, message):
    query = message.text

    async for msg in client.search_messages(CHANNEL_ID, query, limit=5):
        if msg.document or msg.video:
            name = msg.document.file_name if msg.document else msg.video.file_name

            btn = InlineKeyboardMarkup([
                [InlineKeyboardButton("📥 Get File",
                url=f"https://t.me/{(await bot.get_me()).username}?start={msg.id}")]
            ])

            await message.reply(name, reply_markup=btn)

bot.run()
