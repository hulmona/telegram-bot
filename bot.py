import os
import asyncio
from pyrogram import Client, filters
from pymongo import MongoClient

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URI = os.environ.get("MONGO_URI")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID"))
GROUP_ID = int(os.environ.get("GROUP_ID"))

bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

mongo = MongoClient(MONGO_URI)
db = mongo["movies"]
col = db["files"]

# START
@bot.on_message(filters.command("start"))
async def start(client, message):
    await message.reply("Bot working ✅")

# INDEX channel files
@bot.on_message(filters.channel & filters.document)
async def index_files(client, message):
    file_id = message.document.file_id
    file_name = message.document.file_name

    col.insert_one({
        "name": file_name.lower(),
        "file_id": file_id
    })

# SEARCH
@bot.on_message(filters.text & filters.group)
async def search(client, message):
    query = message.text.lower()

    results = col.find({"name": {"$regex": query}}).limit(10)

    buttons = []
    for file in results:
        buttons.append(
            [ 
                (file["name"], f"get_{file['file_id']}")
            ]
        )

    if not buttons:
        return

    txt = "Results:"
    await message.reply(txt)

# SEND FILE
@bot.on_message(filters.private & filters.text)
async def send_file(client, message):
    if message.text.startswith("get_"):
        file_id = message.text.replace("get_","")
        msg = await message.reply_document(file_id)

        await asyncio.sleep(300)
        await msg.delete()

bot.run()
