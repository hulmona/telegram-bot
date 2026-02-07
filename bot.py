from pyrogram import Client, filters
import asyncio

API_ID = 38438389
API_HASH = "327b2592682ff56d760110350e66425e"
BOT_TOKEN = "8298490569:AAGOm3fAOhqBxmvwsB2lrF-mCmvqbG3D7Fo"
CHANNEL_ID = -1003801817080

app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

files = {}

@app.on_message(filters.channel & filters.document)
async def save_file(client, message):
    files[message.document.file_name.lower()] = message.id

@app.on_message(filters.group & filters.text)
async def search(client, message):
    text = message.text.lower()
    results = [name for name in files if text in name]

    if results:
        name = results[0]
        await message.reply(
            f"Found: {name}",
            reply_markup={
                "inline_keyboard":[[
                    {"text":"📥 Download","callback_data":name}
                ]]
            }
        )

@app.on_callback_query()
async def send_file(client, callback_query):
    name = callback_query.data
    msg_id = files.get(name)

    if msg_id:
        sent = await app.copy_message(callback_query.from_user.id, CHANNEL_ID, msg_id)
        await callback_query.answer("File sent in DM")

        await asyncio.sleep(300)
        await sent.delete()

app.run()
