import os
import asyncio
from pyrogram import Client, filters
from motor.motor_asyncio import AsyncIOMotorClient

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
MONGO = os.getenv("MONGO_DB")

bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

mongo = AsyncIOMotorClient(MONGO)
db = mongo["moviebot"]
col = db["files"]

# -------- AUTO SAVE FROM CHANNEL --------
@bot.on_message(filters.channel & filters.document)
async def save_file(client, message):
    name = message.document.file_name
    file_id = message.document.file_id

    await col.update_one(
        {"file_name": name},
        {"$set": {"file_id": file_id}},
        upsert=True
    )

# -------- SEARCH IN GROUP --------
@bot.on_message(filters.group & filters.text)
async def search(client, message):
    text = message.text

    data = await col.find_one(
        {"file_name": {"$regex": text, "$options": "i"}}
    )

    if data:
        file_id = data["file_id"]

        await message.reply(
            f"Result found",
            reply_markup={
                "inline_keyboard": [[
                    {"text": "📥 Download", "callback_data": file_id}
                ]]
            }
        )

# -------- SEND IN DM --------
@bot.on_callback_query()
async def send_file(client, query):
    file_id = query.data
    sent = await bot.send_document(query.from_user.id, file_id)

    await query.answer("Check DM")

    await asyncio.sleep(300)
    await sent.delete()

bot.run()
