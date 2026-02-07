from pyrogram import Client, filters
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

API_ID = 38438389
API_HASH = "327b2592682ff56d760110350e66425e"
BOT_TOKEN = "8298490569:AAGOm3fAOhqBxmvwsB2lrF-mCmvqbG3D7Fo"
CHANNEL_ID = -1003801817080   # minus লাগবে

app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

files = {}

# --------- channel file save ----------
@app.on_message(filters.channel & filters.document)
async def save_file(client, message):
    name = message.document.file_name.lower()
    files[name] = message.id

# --------- search ----------
@app.on_message(filters.group & filters.text)
async def search(client, message):
    text = message.text.lower()
    results = [name for name in files if text in name]

    if results:
        name = results[0]
        await message.reply(
            f"Found: {name}",
            reply_markup={
                "inline_keyboard": [[
                    {"text": "📥 Download", "callback_data": name}
                ]]
            }
        )

# --------- send ----------
@app.on_callback_query()
async def send_file(client, callback_query):
    name = callback_query.data
    msg_id = files.get(name)

    if msg_id:
        sent = await app.copy_message(callback_query.from_user.id, CHANNEL_ID, msg_id)
        await callback_query.answer("Check DM")

        await asyncio.sleep(300)
        await sent.delete()

# --------- render keep alive ----------
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot running")

def run_web():
    server = HTTPServer(("0.0.0.0", 10000), Handler)
    server.serve_forever()

threading.Thread(target=run_web).start()

# --------- start ----------
app.run()
