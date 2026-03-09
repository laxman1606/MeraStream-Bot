import os
import asyncio
from aiohttp import web
from pyrogram import Client, filters
from pyrogram.types import Message

# Credentials safely get karna (taki error na aaye agar khali ho)
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
# Channel ID ko safely integer me convert karna
CHANNEL_ID_STR = os.environ.get("CHANNEL_ID", "0")
CHANNEL_ID = int(CHANNEL_ID_STR) if CHANNEL_ID_STR not in ["", "0", None] else 0
PORT = int(os.environ.get("PORT", 8080))

# Pyrogram Client Setup
app = Client("MeraStreamBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- BOT COMMANDS ---
@app.on_message(filters.command("start"))
async def start_msg(client, message: Message):
    await message.reply_text("👋 Welcome to **MeraStream Bot**!\n\nMhe koi bhi badi video file (1GB+) bhejo, mai tumhe Direct Streaming Link dunga!")

@app.on_message(filters.video | filters.document)
async def handle_video(client, message: Message):
    if CHANNEL_ID == 0:
        await message.reply_text("❌ Error: CHANNEL_ID set nahi hai Render me!")
        return

    msg = await message.reply_text("⏳ Processing your video... Please wait bro!")
    
    try:
        # Video ko DB channel me forward karna
        forwarded_msg = await message.forward(CHANNEL_ID)
        file_id = forwarded_msg.id 
        
        RENDER_URL = os.environ.get("RENDER_URL", "URL_HERE") 
        stream_link = f"{RENDER_URL}/stream/{file_id}"
        
        await msg.edit_text(
            f"✅ **MeraStream Link Generated!**\n\n"
            f"🔗 `MeraStream://play?url={stream_link}`\n\n"
            f"(Ye link tumhare Android app me direct open hoga!)"
        )
    except Exception as e:
        await msg.edit_text(f"❌ Error aagaya bro: {e}")

# --- WEB SERVER (Streaming Logic) ---
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

        file_size = message.video.file_size if message.video else message.document.file_size
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

async def start_services():
    # 1. PEHLE WEB SERVER START KARNA HAI (Render ko khush karne ke liye)
    print("Starting Web Server...")
    webapp = web.Application()
    webapp.add_routes(routes)
    runner = web.AppRunner(webapp)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"✅ Web Server is running on port {PORT}")
    
    # 2. USKE BAAD BOT START KARNA HAI
    print("Starting Telegram Bot...")
    try:
        await app.start()
        print("✅ MeraStream Bot is ALIVE on Telegram!")
    except Exception as e:
        print(f"❌ BOT START FAILED: Please check your API_ID, API_HASH, or BOT_TOKEN. Error: {e}")
    
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(start_services())
