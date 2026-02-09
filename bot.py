import os
import sys
import subprocess
import logging
import threading
from datetime import datetime
import re

# ==================== AUTO INSTALL REQUIREMENTS ====================
# (Kept your auto-installer logic)
try:
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
    from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-telegram-bot==13.15"])
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
    from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext

try:
    from pymongo import MongoClient, TEXT
    from bson import ObjectId
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pymongo"])
    from pymongo import MongoClient, TEXT
    from bson import ObjectId

# ==================== CONFIGURATION ====================
# ⚠️ SECURITY WARNING: Do not hardcode tokens in production! Use Environment Variables.
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
DATABASE_URI = os.getenv("DATABASE_URI", "YOUR_MONGO_DB_URL_HERE")
DATABASE_NAME = os.getenv("DATABASE_NAME", "autofilter")
ADMINS = [int(id) for id in os.getenv("ADMINS", "12345678").split(",") if id.strip()]
BIN_CHANNEL = int(os.getenv("BIN_CHANNEL", "-100xxxxxxxx")) # Channel ID where files are stored
AUTO_DELETE_TIME = int(os.getenv("AUTO_DELETE_TIME", "300"))

# ==================== DATABASE CONNECTION ====================
try:
    mongo_client = MongoClient(DATABASE_URI)
    db = mongo_client[DATABASE_NAME]
    movies_col = db.movies
    
    # Create Index for faster search
    movies_col.create_index([("title", TEXT), ("caption", TEXT)])
    print("✅ MongoDB Connected")
except Exception as e:
    print(f"❌ Database Error: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== HELPER FUNCTIONS ====================
def delete_later(bot, chat_id, message_id, delay):
    def _delete():
        try:
            bot.delete_message(chat_id, message_id)
        except Exception:
            pass
    threading.Timer(delay, _delete).start()

def get_file_details(message):
    """Extracts media details from a message"""
    media = message.video or message.document or message.audio
    if media:
        file_name = getattr(media, 'file_name', '')
        # If no filename (e.g. video), use caption or generate one
        if not file_name:
            file_name = message.caption or "Unknown_File"
        
        return {
            "file_id": media.file_id,
            "file_unique_id": media.file_unique_id,
            "file_name": file_name,
            "file_size": media.file_size,
            "caption": message.caption or file_name,
            "mime_type": getattr(media, 'mime_type', 'unknown')
        }
    return None

# ==================== 1. INDEXER HANDLER (NEW!) ====================
def index_files(update: Update, context: CallbackContext):
    """Saves files from BIN_CHANNEL to MongoDB"""
    msg = update.effective_message
    
    # Only index files from the specific Bin Channel
    if msg.chat.id != BIN_CHANNEL:
        return

    media = get_file_details(msg)
    if media:
        # Avoid duplicates based on unique ID
        if movies_col.find_one({'file_unique_id': media['file_unique_id']}):
            return 

        # Normalize title for better search
        # Replaces dots/underscores with spaces
        clean_title = re.sub(r'[._-]', ' ', media['file_name'])
        
        movie_data = {
            'file_id': media['file_id'],
            'file_unique_id': media['file_unique_id'],
            'title': clean_title,
            'caption': media['caption'],
            'size': f"{media['file_size'] / (1024*1024):.2f} MB",
            'date': datetime.now()
        }
        
        try:
            movies_col.insert_one(movie_data)
            logger.info(f"➕ Indexed: {clean_title}")
        except Exception as e:
            logger.error(f"Error indexing: {e}")

# ==================== 2. SEARCH HANDLER ====================
def auto_filter(update: Update, context: CallbackContext):
    msg = update.effective_message
    query = msg.text
    
    if not query or len(query) < 3:
        return

    # Regex Search (More powerful than Text Search)
    # This finds "Avengers" even if you type "avenger"
    regex = re.compile(re.escape(query), re.IGNORECASE)
    
    results = list(movies_col.find({"title": regex}).limit(10))

    if not results:
        # Optional: Reply if not found
        # msg.reply_text("❌ No results found.")
        return

    buttons = []
    for movie in results:
        # Create a button for each movie
        btn_text = f"🎬 {movie['title'][:30]}... [{movie['size']}]"
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"get_{str(movie['_id'])}")])

    msg.reply_text(
        f"🔎 **Found {len(results)} results for:** `{query}`",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )

# ==================== 3. CALLBACK HANDLER ====================
def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    
    if data.startswith("get_"):
        file_oid = data.split("_")[1]
        try:
            movie = movies_col.find_one({"_id": ObjectId(file_oid)})
            if not movie:
                query.answer("File not found in DB!", show_alert=True)
                return
            
            query.answer()
            
            caption = f"🎬 **{movie['title']}**\n📦 Size: {movie['size']}\n\n⚠️ *Auto-delete in 5 mins*"
            
            sent_msg = context.bot.send_document(
                chat_id=query.message.chat_id,
                document=movie['file_id'],
                caption=caption,
                parse_mode="Markdown"
            )
            
            # Auto Delete
            delete_later(context.bot, sent_msg.chat.id, sent_msg.id, AUTO_DELETE_TIME)
            
        except Exception as e:
            query.answer(f"Error: {e}", show_alert=True)

# ==================== MAIN ====================
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # 1. Index Handler (Listens to Channel Posts)
    # This specifically listens to the BIN_CHANNEL
    dp.add_handler(MessageHandler(Filters.chat(BIN_CHANNEL) & (Filters.document | Filters.video), index_files))

    # 2. Search Handler (Listens to Group Text)
    dp.add_handler(MessageHandler(Filters.text & Filters.group & ~Filters.command, auto_filter))

    # 3. Callback Handler
    dp.add_handler(CallbackQueryHandler(button_callback))
    
    # 4. Start Command
    dp.add_handler(CommandHandler("start", lambda u,c: u.message.reply_text("Bot is Online! Add me to a group.")))

    print("🤖 Bot Started...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
