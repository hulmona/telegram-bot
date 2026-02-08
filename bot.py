import os
import asyncio
import threading
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

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
GROUP_ID = int(os.environ.get("GROUP_ID", "0"))

bot = Client("moviebot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ---------------- START DM ----------------
@bot.on_message(filters.command("start") & filters.private)
async def start(client, message):
    if len(message.command) == 1:
        await message.reply_text(
            "👋 হ্যালো!\n\n"
            "🎬 মুভি পেতে গ্রুপে গিয়ে মুভির নাম লিখুন।"
        )
        return

    try:
        file_id = int(message.command[1])
        
        # BIN_CHANNEL থেকে file নিয়ে আসা
        msg = await client.get_messages(BIN_CHANNEL, file_id)
        
        # User এর DM এ file পাঠানো
        sent = await msg.copy(message.chat.id)
        
        # Warning message
        warn = await message.reply_text(
            "🛡️ **Security Notice:**\n"
            "ফাইলটি ৫ মিনিট পর স্বয়ংক্রিয়ভাবে ডিলিট হয়ে যাবে।\n\n"
            "⏰ এখনই ডাউনলোড করে নিন!"
        )
        
        # 5 মিনিট (300 সেকেন্ড) অপেক্ষা করা
        await asyncio.sleep(300)
        
        # File এবং warning message ডিলিট করা
        try:
            await sent.delete()
            await warn.delete()
        except Exception as del_error:
            print(f"Delete error: {del_error}")
            
    except ValueError:
        await message.reply_text("❌ Invalid file link!")
    except Exception as e:
        await message.reply_text(f"❌ Error: File not found!")
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
    results_count = 0
    max_results = 10

    try:
        async for msg in client.search_messages(BIN_CHANNEL, query=query, limit=50):
            media = msg.document or msg.video or msg.audio or msg.animation
            
            if media:
                name = getattr(media, 'file_name', 'File')
                file_id = msg.id
                
                # File size দেখানো (যদি থাকে)
                size = getattr(media, 'file_size', 0)
                size_mb = size / (1024 * 1024) if size else 0
                
                # Button তৈরি করা
                btn = InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "📥 Get File", 
                        url=f"https://t.me/{bot_info.username}?start={file_id}"
                    )
                ]])
                
                # Result পাঠানো
                caption = f"✅ **Found:**\n📁 {name}"
                if size_mb > 0:
                    caption += f"\n📊 Size: {size_mb:.2f} MB"
                
                await message.reply_text(caption, reply_markup=btn)
                
                results_count += 1
                
                # Maximum result limit
                if results_count >= max_results:
                    await message.reply_text(
                        f"📌 প্রথম {max_results}টি রেজাল্ট দেখানো হয়েছে।\n"
                        "আরও specific নাম দিয়ে search করুন।"
                    )
                    break
                
                # Flood protection
                await asyncio.sleep(0.5)
        
        # কোনো result না পেলে
        if results_count == 0:
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
    
    # "Searching..." message ডিলিট করা
    try:
        await wait.delete()
    except:
        pass

# ---------------- RUN ----------------
if __name__ == "__main__":
    # Web server background এ চালানো
    threading.Thread(target=run_web, daemon=True).start()
    
    print("🚀 Bot starting...")
    print("✅ Web server running on port 10000")
    
    # Bot চালানো
    bot.run()
