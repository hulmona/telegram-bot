import os
import asyncio
import threading
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ---------------- WEB ----------------
app = Flask(__name__)
@app.route("/")
def home(): return "Bot running"
def run_web(): app.run(host="0.0.0.0", port=10000)

# ---------------- ENV ----------------
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
BIN_CHANNEL = int(os.environ.get("BIN_CHANNEL"))
# যদি নির্দিষ্ট গ্রুপে কাজ করাতে চান তবে GROUP_ID দিন, নয়তো filters.group ব্যবহার করুন
GROUP_ID = int(os.environ.get("GROUP_ID", 0)) 

bot = Client("moviebot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ---------------- START DM ----------------
@bot.on_message(filters.command("start") & filters.private)
async def start(client, message):
    if len(message.command) == 1:
        await message.reply_text("মুভির নাম গ্রুপে লিখুন।")
        return

    file_id = int(message.command[1])
    try:
        msg = await client.get_messages(BIN_CHANNEL, file_id)
        sent = await msg.copy(message.chat.id)
        warn = await message.reply_text("🛡️ ফাইলটি ৫ মিনিট পর ডিলিট হয়ে যাবে।")
        
        await asyncio.sleep(300)
        await sent.delete()
        await warn.delete()
    except Exception as e:
        await message.reply_text(f"Error: {e}")

# ---------------- SEARCH LOGIC ----------------
# এখানে filters.chat(GROUP_ID) দিলে শুধু ওই গ্রুপে কাজ করবে
# সব গ্রুপে কাজ করাতে চাইলে শুধু filters.group দিন
@bot.on_message(filters.text & filters.group)
async def search(client, message):
    query = message.text
    if len(query) < 3: return # ছোট টেক্সটে সার্চ করবে না

    wait = await message.reply_text("🔎 Searching...")
    bot_info = await client.get_me()
    results_found = False

    try:
        async for msg in client.search_messages(BIN_CHANNEL, query=query):
            media = msg.document or msg.video or msg.audio or msg.animation
            if media:
                results_found = True
                name = getattr(media, 'file_name', 'File')
                file_id = msg.id

                btn = InlineKeyboardMarkup(
                    [[InlineKeyboardButton("📥 Get File", 
                    url=f"https://t.me/{bot_info.username}?start={file_id}")]]
                )
                await message.reply_text(f"✅ Found: **{name}**", reply_markup=btn)
        
        if not results_found:
            await message.reply_text("❌ দুঃখিত, আপনার নামে কোনো মুভি পাওয়া যায়নি।")
            
    except Exception as e:
        print(f"Error: {e}")
    
    await wait.delete()

# ---------------- RUN ----------------
if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    bot.run()
