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
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
BIN_CHANNEL = int(os.environ.get("BIN_CHANNEL", "0"))
DATABASE_URI = os.environ.get("DATABASE_URI", "")
DATABASE_NAME = os.environ.get("DATABASE_NAME", "autofilter")
ADMINS = list(map(int, os.environ.get("ADMINS", "7916138581").split()))

# MongoDB Setup
mongo_client = AsyncIOMotorClient(DATABASE_URI)
db = mongo_client[DATABASE_NAME]
files_collection = db.files

bot = Client("moviebot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ---------------- INDEX FILES ----------------
@bot.on_message(filters.command("index") & filters.private)
async def index_files(client, message):
    """Admin command: BIN_CHANNEL এর সব file database এ save করা"""
    user_id = message.from_user.id
    
    if user_id not in ADMINS:
        await message.reply_text("❌ You are not authorized!")
        return
    
    status = await message.reply_text("📥 Indexing started...")
    count = 0
    
    try:
        async for msg in client.get_chat_history(BIN_CHANNEL):
            media = msg.document or msg.video or msg.audio or msg.animation
            
            if media:
                file_name = getattr(media, 'file_name', 'File')
                file_size = getattr(media, 'file_size', 0)
                file_id = msg.id
                
                # Database এ save করা
                await files_collection.update_one(
                    {"file_id": file_id},
                    {
                        "$set": {
                            "file_id": file_id,
                            "file_name": file_name,
                            "file_size": file_size,
                            "file_type": getattr(media, 'mime_type', None)
                        }
                    },
                    upsert=True
                )
                
                count += 1
                
                if count % 100 == 0:
                    await status.edit_text(f"📥 Indexed: {count} files...")
        
        await status.edit_text(f"✅ Indexing Complete!\n📊 Total Files: {count}")
        
    except Exception as e:
        await status.edit_text(f"❌ Error: {e}")
        print(f"Indexing error: {e}")

# ---------------- STATS COMMAND ----------------
@bot.on_message(filters.command("stats") & filters.private)
async def stats(client, message):
    """Database stats"""
    user_id = message.from_user.id
    
    if user_id not in ADMINS:
        return
    
    try:
        total = await files_collection.count_documents({})
        await message.reply_text(f"📊 **Total Files:** {total:,}")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

# ---------------- START DM ----------------
@bot.on_message(filters.command("start") & filters.private)
async def start(client, message):
    if len(message.command) == 1:
        await message.reply_text(
            "👋 **হ্যালো!**\n\n"
            "🎬 মুভি পেতে গ্রুপে গিয়ে মুভির নাম লিখুন।\n\n"
            "💡 **Features:**\n"
            "• Fast Search\n"
            "• Auto Delete (5 min)\n"
            "• 40,000+ Movies"
        )
        return

    try:
        file_id = int(message.command[1])
        
        # BIN_CHANNEL থেকে file নিয়ে আসা
        msg = await client.get_messages(BIN_CHANNEL, file_id)
        
        if not msg:
            await message.reply_text("❌ File not found!")
            return
        
        # User এর DM এ file পাঠানো
        sent = await msg.copy(message.chat.id)
        
        # Warning message
        warn = await message.reply_text(
            "🛡️ **Security Notice:**\n"
            "ফাইলটি **৫ মিনিট** পর স্বয়ংক্রিয়ভাবে ডিলিট হয়ে যাবে।\n\n"
            "⏰ এখনই ডাউনলোড করে নিন!"
        )
        
        # 5 মিনিট অপেক্ষা
        await asyncio.sleep(300)
        
        # ডিলিট করা
        try:
            await sent.delete()
            await warn.delete()
        except Exception as del_error:
            print(f"Delete error: {del_error}")
            
    except ValueError:
        await message.reply_text("❌ Invalid file link!")
    except Exception as e:
        await message.reply_text("❌ Error: File not found!")
        print(f"Start command error: {e}")

# ---------------- SEARCH LOGIC ----------------
@bot.on_message(filters.text & filters.group)
async def search(client, message):
    query = message.text.strip()
    
    # ছোট text বা command ignore করা
    if len(query) < 3 or query.startswith("/"):
        return

    wait = await message.reply_text("🔎 Searching...")
    bot_info = await client.get_me()
    max_results = 10

    try:
        # MongoDB তে regex search (case-insensitive)
        search_results = files_collection.find(
            {"file_name": {"$regex": query, "$options": "i"}}
        ).limit(max_results)
        
        results_list = await search_results.to_list(length=max_results)
        
        if results_list:
            for result in results_list:
                name = result.get("file_name", "File")
                file_id = result.get("file_id")
                size = result.get("file_size", 0)
                size_mb = size / (1024 * 1024) if size else 0
                size_gb = size_mb / 1024
                
                # Button তৈরি
                btn = InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "📥 Get File", 
                        url=f"https://t.me/{bot_info.username}?start={file_id}"
                    )
                ]])
                
                # Result পাঠানো
                caption = f"✅ **Found:**\n📁 `{name}`"
                
                if size_gb >= 1:
                    caption += f"\n📊 Size: **{size_gb:.2f} GB**"
                elif size_mb > 0:
                    caption += f"\n📊 Size: **{size_mb:.2f} MB**"
                
                caption += "\n\n⚠️ *Auto-delete: 5 minutes*"
                
                await message.reply_text(caption, reply_markup=btn)
                await asyncio.sleep(0.5)  # Flood protection
        else:
            await message.reply_text(
                "❌ দুঃখিত, আপনার নামে কোনো মুভি পাওয়া যায়নি।\n\n"
                "💡 **Tips:**\n"
                "• সঠিক spelling দিয়ে চেষ্টা করুন\n"
                "• English নাম দিয়ে search করুন\n"
                "• শুধু মুভির মূল নাম লিখুন"
            )
            
    except Exception as e:
        print(f"Search Error: {e}")
        await message.reply_text("⚠️ Search করতে সমস্যা হয়েছে। আবার চেষ্টা করুন।")
    
    try:
        await wait.delete()
    except:
        pass

# ---------------- RUN ----------------
if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    
    print("=" * 50)
    print("🚀 Bot starting...")
    print("✅ Web server: http://0.0.0.0:10000")
    print("🗄️ MongoDB: Connected")
    print("=" * 50)
    
    bot.run()
