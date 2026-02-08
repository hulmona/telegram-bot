import os
import asyncio
import threading
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient

# ---------------- WEB SERVER (For 24/7) ----------------
app = Flask(__name__)
@app.route("/")
def home(): return "Bot is Running Securely"
def run_web(): app.run(host="0.0.0.0", port=10000)

# ---------------- ENV VARIABLES ----------------
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
BIN_CHANNEL = int(os.environ.get("BIN_CHANNEL"))
GROUP_ID = int(os.environ.get("GROUP_ID", 0))
ADMINS = [int(x) for x in os.environ.get("ADMINS", "").split()]

# Database setup
DATABASE_URI = os.environ.get("DATABASE_URI")
DATABASE_NAME = os.environ.get("DATABASE_NAME", "Cluster0")
mongo = AsyncIOMotorClient(DATABASE_URI)
db = mongo[DATABASE_NAME]
movies_col = db['movies']

bot = Client("moviebot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ---------------- START COMMAND ----------------
@bot.on_message(filters.command("start") & filters.private)
async def start(client, message):
    if len(message.command) == 1:
        await message.reply_text(
            f"👋 Hello {message.from_user.mention}!\n\n"
            "আমি একটি মুভি সার্চ বট। মুভি পেতে আমাদের গ্রুপে জয়েন করুন এবং মুভির নাম লিখুন।"
        )
        return

    # If coming from group link
    file_id = int(message.command[1])
    try:
        msg = await client.get_messages(BIN_CHANNEL, file_id)
        sent = await msg.copy(message.chat.id)
        warn = await message.reply_text("⚠️ **নিরাপত্তার স্বার্থে ফাইলটি ৫ মিনিট পর ডিলিট হয়ে যাবে।**")
        
        await asyncio.sleep(300) # 5 minutes
        await sent.delete()
        await warn.delete()
    except Exception as e:
        await message.reply_text("❌ ফাইলটি খুঁজে পাওয়া যায়নি বা ডিলিট হয়ে গেছে।")

# ---------------- INDEX COMMAND (For Admin) ----------------
@bot.on_message(filters.command("index") & filters.user(ADMINS))
async def index_files(client, message):
    m = await message.reply_text("Indexing files... Please wait.")
    count = 0
    async for msg in client.get_chat_history(BIN_CHANNEL):
        media = msg.document or msg.video
        if media:
            file_name = getattr(media, 'file_name', 'No Name')
            # Save to Database
            await movies_col.update_one(
                {"file_id": msg.id},
                {"$set": {"file_name": file_name.lower(), "original_name": file_name}},
                upsert=True
            )
            count += 1
    await m.edit(f"✅ Indexing Complete! {count} files saved.")

# ---------------- SEARCH LOGIC (In Group) ----------------
@bot.on_message(filters.text & filters.group)
async def search(client, message):
    query = message.text.lower()
    if len(query) < 3: return

    # Search in Database (Fuzzy Search)
    cursor = movies_col.find({"file_name": {"$regex": query}})
    results = await cursor.to_list(length=10)

    if not results:
        # Fallback to Telegram Search if DB is empty
        found = False
        bot_info = await client.get_me()
        async for msg in client.search_messages(BIN_CHANNEL, query=query, limit=5):
            media = msg.document or msg.video
            if media:
                found = True
                name = getattr(media, 'file_name', 'File')
                btn = InlineKeyboardMarkup([[InlineKeyboardButton("📥 Get File", url=f"https://t.me/{bot_info.username}?start={msg.id}")]])
                await message.reply_text(f"✅ **Found:** {name}", reply_markup=btn)
        
        if not found:
            await message.reply_text("❌ মুভিটি পাওয়া যায়নি। দয়া করে বানান চেক করুন।")
        return

    # If results found in DB
    bot_info = await client.get_me()
    for movie in results:
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("📥 Get File", url=f"https://t.me/{bot_info.username}?start={movie['file_id']}")]])
        await message.reply_text(f"✅ **Found:** {movie['original_name']}", reply_markup=btn)

# ---------------- RUN BOT ----------------
if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    print("Bot is starting...")
    bot.run()

