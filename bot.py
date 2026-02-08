import os
import logging
import asyncio
import threading
from datetime import datetime, timedelta
from bson import ObjectId
from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters as tg_filters, ContextTypes

# ==================== CONFIGURATION ====================
API_ID = int(os.getenv("API_ID", "38438389"))
API_HASH = os.getenv("API_HASH", "327b2592682ff56d760110350e66425e")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8298490569:AAGOm3fAOhqBxmvwsB2lrF-mCmvqbG3D7Fo")

DATABASE_URI = os.getenv("DATABASE_URI", "mongodb+srv://moviebot:Movie%4012345@cluster0.3qgtiud.mongodb.net/?retryWrites=true&w=majority")
DATABASE_NAME = os.getenv("DATABASE_NAME", "autofilter")

ADMINS = list(map(int, os.getenv("ADMINS", "7916138581").split(",")))
BIN_CHANNEL = int(os.getenv("BIN_CHANNEL", "-1003801817080"))
FORCE_SUB = os.getenv("FORCE_SUB", "")  # Force subscribe channel

AUTO_FFILTER = os.getenv("AUTO_FFILTER", "True") == "True"
SPELL_CHECK_REPLY = os.getenv("SPELL_CHECK_REPLY", "True") == "True"
MAX_BTN = int(os.getenv("MAX_BTN", "10"))
AUTO_DELETE = os.getenv("AUTO_DELETE", "True") == "True"
AUTO_DELETE_TIME = int(os.getenv("AUTO_DELETE_TIME", "300"))  # 5 minutes

# ==================== LOGGING ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== DATABASE ====================
try:
    mongo_client = MongoClient(DATABASE_URI)
    db = mongo_client[DATABASE_NAME]
    
    # Collections
    movies_col = db.movies
    users_col = db.users
    groups_col = db.groups
    
    # Create indexes
    movies_col.create_index([("title", "text"), ("caption", "text")])
    movies_col.create_index("file_id", unique=True)
    users_col.create_index("user_id", unique=True)
    groups_col.create_index("chat_id", unique=True)
    
    logger.info("✅ MongoDB connected successfully")
except Exception as e:
    logger.error(f"❌ MongoDB connection failed: {e}")
    raise

# ==================== HELPER FUNCTIONS ====================
def delete_later(bot, chat_id, message_id, delay=AUTO_DELETE_TIME):
    """Delete message after specified delay"""
    def delete():
        try:
            asyncio.run(bot.delete_message(chat_id=chat_id, message_id=message_id))
        except Exception as e:
            logger.error(f"Delete error: {e}")
    
    threading.Timer(delay, delete).start()

async def save_user(user_id, username=""):
    """Save user to database"""
    try:
        users_col.update_one(
            {"user_id": user_id},
            {"$set": {"username": username, "joined_at": datetime.now()}},
            upsert=True
        )
    except Exception as e:
        logger.error(f"Save user error: {e}")

async def save_group(chat_id, title=""):
    """Save group to database"""
    try:
        groups_col.update_one(
            {"chat_id": chat_id},
            {"$set": {"title": title, "added_at": datetime.now()}},
            upsert=True
        )
    except Exception as e:
        logger.error(f"Save group error: {e}")

# ==================== TELEGRAM BOT HANDLERS ====================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    await save_user(user.id, user.username)
    
    welcome_text = f"""
👋 **হ্যালো {user.first_name}!**

🤖 **আমি একটি অটো মুভি সার্চ বট**
🎬 **20,000+ মুভি ডাটাবেজ**
⚡ **অটো সার্চ & অটো ডিলিট**

📌 **ইউজেজ:**
1. আমাকে কোনো গ্রুপে এড করুন (Admin দিতে হবে)
2. গ্রুপে মুভির নাম লিখুন
3. আমি সার্চ করে ফলাফল দিব
4. বাটনে ক্লিক করে মুভি ডাউনলোড করুন

⚠️ **সতর্কতা:**
• মুভি ফাইল ৫ মিনিট পর অটো ডিলিট হয়ে যাবে
• ফাইল অন্য চ্যাটে ফরওয়ার্ড করে ডাউনলোড শুরু করুন

🔗 **সাপোর্ট গ্রুপ:** @Graduate_Request
    """
    
    keyboard = [
        [InlineKeyboardButton("📢 আপডেট চ্যানেল", url="https://t.me/Graduate_Movies")],
        [InlineKeyboardButton("📞 সাপোর্ট গ্রুপ", url="https://t.me/Graduate_Request")],
        [InlineKeyboardButton("➕ গ্রুপে এড করুন", url=f"https://t.me/{context.bot.username}?startgroup=true")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
🆘 **হেল্প মেনু:**

🔍 **সার্চ করতে:**
গ্রুপে শুধু মুভির নাম লিখুন

⚙️ **এডমিন কমান্ড:**
• /stats - বট স্ট্যাটাস
• /broadcast - ব্রডকাস্ট মেসেজ
• /index - ডাটাবেজ ইন্ডেক্স

📌 **ফিচারস:**
• অটো মুভি সার্চ
• ইনলাইন বাটন রেজাল্ট
• অটো ডিলিট ৫ মিনিট পর
• 20K+ মুভি ডাটাবেজ
• বাংলা ইংলিশ সব ভাষা

🔗 **চ্যানেল:** @Graduate_Movies
👥 **গ্রুপ:** @Graduate_Request
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command (admin only)"""
    user_id = update.effective_user.id
    if user_id not in ADMINS:
        await update.message.reply_text("❌ এই কমান্ড শুধু এডমিনদের জন্য।")
        return
    
    try:
        total_movies = movies_col.count_documents({})
        total_users = users_col.count_documents({})
        total_groups = groups_col.count_documents({})
        
        stats_text = f"""
📊 **বট স্ট্যাটিস্টিক্স:**

🎬 **মোট মুভি:** {total_movies}
👤 **মোট ইউজার:** {total_users}
👥 **মোট গ্রুপ:** {total_groups}
⏰ **আপটাইম:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        await update.message.reply_text(stats_text, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ স্ট্যাটস লোড করতে সমস্যা: {e}")

async def auto_filter_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle auto filter in groups"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    query = update.message.text.strip()
    
    # Save group info
    await save_group(chat_id, update.effective_chat.title)
    
    if not query or len(query) < 2:
        return
    
    logger.info(f"Search query: {query} from {user_id} in {chat_id}")
    
    # Search in database
    try:
        results = list(movies_col.find(
            {"$text": {"$search": query}},
            {"score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})]).limit(MAX_BTN))
        
        if not results:
            if SPELL_CHECK_REPLY:
                await update.message.reply_text("❌ এই নামে কোনো মুভি পাওয়া যায়নি।")
            return
        
        buttons = []
        for movie in results:
            title = movie.get('title', 'Unknown')[:35]
            quality = movie.get('quality', 'N/A')
            size = movie.get('size', 'N/A')
            year = movie.get('year', '')
            
            button_text = f"🎬 {title}"
            if year:
                button_text += f" ({year})"
            button_text += f" | {quality} | {size}"
            
            buttons.append([InlineKeyboardButton(button_text, callback_data=f"movie_{movie['_id']}")])
        
        # Add page navigation if many results
        if len(results) == MAX_BTN:
            buttons.append([InlineKeyboardButton("📖 আরো রেজাল্ট দেখুন", callback_data=f"next_1_{query}")])
        
        reply_markup = InlineKeyboardMarkup(buttons)
        
        result_msg = await update.message.reply_text(
            f"🔍 **'{query}'** এর জন্য {len(results)}টি রেজাল্ট:\n\n"
            "⬇️ নিচের বাটনে ক্লিক করে মুভি ডাউনলোড করুন:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        # Auto delete search results after 2 minutes
        if AUTO_DELETE:
            delete_later(context.bot, chat_id, result_msg.message_id, 120)
            
    except Exception as e:
        logger.error(f"Search error: {e}")
        await update.message.reply_text("❌ সার্চ করতে সমস্যা হয়েছে।")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    
    logger.info(f"Callback: {data} from {user_id}")
    
    if data.startswith("movie_"):
        # Send movie file
        movie_id = data.split("_")[1]
        
        try:
            movie = movies_col.find_one({"_id": ObjectId(movie_id)})
            if not movie:
                await query.edit_message_text("❌ মুভিটি পাওয়া যায়নি।")
                return
            
            # Prepare caption
            caption = f"""
🎬 **{movie.get('title', 'Unknown')}**
📅 ইয়ার: {movie.get('year', 'N/A')}
🗂 কোয়ালিটি: {movie.get('quality', 'N/A')}
📦 সাইজ: {movie.get('size', 'N/A')}
🎭 জেনার: {movie.get('genre', 'N/A')}
🌍 ভাষা: {movie.get('language', 'N/A')}

⚠️ **গুরুত্বপূর্ণ ⚠️**
এই মুভি ফাইলটি {AUTO_DELETE_TIME//60} মিনিট পর অটো ডিলিট হয়ে যাবে (কপিরাইট ইস্যু)। 
**অনুগ্রহ করে এই ফাইলটি অন্য কোথাও ফরওয়ার্ড করুন এবং সেখানে ডাউনলোড শুরু করুন।**
            """
            
            # Send movie file
            try:
                file_msg = await context.bot.send_document(
                    chat_id=chat_id,
                    document=movie['file_id'],
                    caption=caption,
                    parse_mode='Markdown'
                )
                
                # Auto delete movie after specified time
                if AUTO_DELETE:
                    delete_later(context.bot, chat_id, file_msg.message_id, AUTO_DELETE_TIME)
                
                # Send reminder
                reminder_text = f"""
⏰ **রিমাইন্ডার**
এই ফাইলটি {AUTO_DELETE_TIME//60} মিনিট পর ডিলিট হবে।
দ্রুত অন্য চ্যাটে **ফরওয়ার্ড** করুন এবং ডাউনলোড শুরু করুন!
                """
                reminder_msg = await context.bot.send_message(chat_id, reminder_text)
                delete_later(context.bot, chat_id, reminder_msg.message_id, AUTO_DELETE_TIME - 60)
                
            except Exception as e:
                logger.error(f"Send document error: {e}")
                await query.edit_message_text("❌ ফাইল সেন্ড করতে সমস্যা হয়েছে।")
        
        except Exception as e:
            logger.error(f"Movie fetch error: {e}")
            await query.edit_message_text("❌ মুভি লোড করতে সমস্যা হয়েছে।")
    
    elif data.startswith("next_"):
        # Handle pagination (implement if needed)
        await query.edit_message_text("📖 পরের পেজ ডেভেলপমেন্ট চলছে...")

# ==================== PYROGRAM CLIENT FOR FILE INDEXING ====================
async def index_files():
    """Index files from BIN_CHANNEL to MongoDB"""
    try:
        app = Client(
            "movie_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            in_memory=True
        )
        
        await app.start()
        logger.info("✅ Pyrogram client started for indexing")
        
        total_indexed = 0
        async for message in app.get_chat_history(BIN_CHANNEL):
            if message.document or message.video:
                file_id = message.document.file_id if message.document else message.video.file_id
                
                # Check if already indexed
                if movies_col.find_one({"file_id": file_id}):
                    continue
                
                # Extract metadata from caption
                caption = message.caption or ""
                lines = caption.split('\n')
                
                movie_data = {
                    "file_id": file_id,
                    "message_id": message.id,
                    "caption": caption,
                    "title": lines[0] if lines else "Unknown",
                    "quality": "720p",
                    "size": "2.10 GB",
                    "year": "2020",
                    "language": "Hindi",
                    "genre": "Action",
                    "indexed_at": datetime.now()
                }
                
                # Try to extract info from caption
                for line in lines:
                    line_lower = line.lower()
                    if '720p' in line_lower:
                        movie_data["quality"] = "720p"
                    elif '1080p' in line_lower:
                        movie_data["quality"] = "1080p"
                    elif '480p' in line_lower:
                        movie_data["quality"] = "480p"
                    
                    if 'gb' in line_lower:
                        movie_data["size"] = line.split('|')[0].strip()
                
                movies_col.insert_one(movie_data)
                total_indexed += 1
                
                if total_indexed % 100 == 0:
                    logger.info(f"Indexed {total_indexed} files...")
        
        await app.stop()
        logger.info(f"✅ Total indexed files: {total_indexed}")
        
    except Exception as e:
        logger.error(f"Indexing error: {e}")

# ==================== MAIN FUNCTION ====================
def main():
    """Main function to run the bot"""
    # Create Telegram Bot Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # Auto filter handler for groups
    if AUTO_FFILTER:
        application.add_handler(MessageHandler(
            tg_filters.TEXT & ~tg_filters.COMMAND & tg_filters.ChatType.GROUPS,
            auto_filter_handler
        ))
    
    # Callback query handler
    application.add_handler(CallbackQueryHandler(callback_handler))
    
    # Run indexing on startup (in background)
    if API_ID and API_HASH:
        threading.Thread(target=lambda: asyncio.run(index_files()), daemon=True).start()
    
    # Start webhook for Render.com
    port = int(os.environ.get("PORT", 8443))
    webhook_url = f"https://your-app-name.onrender.com/{BOT_TOKEN}"
    
    logger.info(f"🚀 Starting bot on port {port}")
    logger.info(f"🌐 Webhook URL: {webhook_url}")
    
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=BOT_TOKEN,
        webhook_url=webhook_url,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()
