import asyncio
# MAGIC TRICK: Pyrogram import hone se pehle Event Loop bana do!
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

import os
from aiohttp import web
from pyrogram import Client, filters, idle
from pyrogram.types import Message

# Tumhare environment variables ko safely extract karna
API_ID_STR = os.environ.get("API_ID", "").strip()
API_HASH = os.environ.get("API_HASH", "").strip()
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()

# Safely API_ID aur CHANNEL_ID ko integer me convert karna
try:
    API_ID = int(API_ID_STR)
except ValueError:
    API_ID = 0

CHANNEL_ID_STR = os.environ.get("CHANNEL_ID", "0").strip()
try:
    CHANNEL_ID = int(CHANNEL_ID_STR)
except ValueError:
    CHANNEL_ID = 0

PORT = int(os.environ.get("PORT", 8080))

# Pyrogram Client - Yahan sirf setup hai
app = Client(
    "MeraStreamBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ==========================================
# 🤖 BOT COMMANDS (TELEGRAM LOGIC)
# ==========================================

@app.on_message(filters.command("start"))
async def start_msg(client, message: Message):
    await message.reply_text("👋 Welcome to **MeraStream Bot**!\n\nMhe koi bhi badi video file (1GB+) bhejo, mai tumhe Direct Streaming Link dunga!")

@app.on_message(filters.video | filters.document)
async def handle_video(client, message: Message):
    if CHANNEL_ID == 0:
        await message.reply_text("❌ Error: CHANNEL_ID set nahi hai Render me! (Check environment variables)")
        return

    msg = await message.reply_text("⏳ Processing your video... Please wait bro!")
    
    try:
        # Video ko DB channel me forward karna
        forwarded_msg = await message.forward(CHANNEL_ID)
        file_id = forwarded_msg.id 
        
        RENDER_URL = os.environ.get("RENDER_URL", "").strip()
        # Agar URL ke last me '/' hai to hata do
        if RENDER_URL.endswith('/'):
            RENDER_URL = RENDER_URL[:-1]
            
        stream_link = f"{RENDER_URL}/stream/{file_id}"
        
        await msg.edit_text(
            f"✅ **MeraStream Link Generated!**\n\n"
            f"🔗 `MeraStream://play?url={stream_link}`\n\n"
            f"(Ye link tumhare Android app me direct open hoga!)"
        )
    except Exception as e:
        await msg.edit_text(f"❌ Error aagaya bro: {e}")

# ==========================================
# 🌐 WEB SERVER (STREAMING LOGIC)
# ==========================================

routes = web.RouteTableDef()

@routes.get('/')
async def hello(request):
    return web.Response(text="✅ MeraStream Server is Running Perfectly! 🔥")

@routes.get('/stream/{msg_id}')
async def stream_video(request):
    msg_id = int(request.match_info['msg_id'])
    
    try:
        message = await app.get_messages(CHANNEL_ID, msg_id)
        if not message or not (message.video or message.document):
            return web.Response(status=404, text="Video Not Found")

        mime_type = message.video.mime_type if message.video else message.document.mime_type

        headers = {
            'Content-Type': mime_type or 'application/octet-stream',
            'Accept-Ranges': 'bytes',
        }
        
        async def my_iter():
            async for chunk in app.stream_media(message):
                yield chunk

        response = web.StreamResponse(headers=headers, status=200)
        await response.prepare(request)
        
        async for chunk in my_iter():
            await response.write(chunk)
            
        return response

    except Exception as e:
        return web.Response(status=500, text=str(e))

# ==========================================
# 🚀 MAIN FUNCTION (DONO KO EK SATH CHALANA)
# ==========================================

async def main():
    print("🌐 Starting Web Server...")
    webapp = web.Application()
    webapp.add_routes(routes)
    runner = web.AppRunner(webapp)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"✅ Web Server started on port {PORT}")

    print("🤖 Starting Telegram Bot...")
    try:
        await app.start()
        print("✅ MeraStream Bot is ALIVE on Telegram!")
    except Exception as e:
        print(f"❌ BOT START FAILED: {e}")
        return # Agar bot fail hua to aage badhne ka fayda nahi

    print("🔥 Everything is running. Waiting for messages...")
    await idle()
    
    print("🛑 Stopping services...")
    await app.stop()
    await runner.cleanup()

if __name__ == "__main__":
    loop.run_until_complete(main())
