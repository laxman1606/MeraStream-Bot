import os
import asyncio
from aiohttp import web
from pyrogram import Client, filters
from pyrogram.types import Message

# Tumhare Credentials yahan aayenge (Render me hum isko hide karenge)
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID"))
PORT = int(os.environ.get("PORT", 8080))

# Pyrogram Client Setup
app = Client("MeraStreamBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Jab koi /start bheje
@app.on_message(filters.command("start"))
async def start_msg(client, message: Message):
    await message.reply_text("👋 Welcome to **MeraStream Bot**!\n\nMhe koi bhi badi video file (1GB+) bhejo, mai tumhe Direct Streaming Link dunga jise tum MeraStream App me chala sakte ho!")

# Jab koi Video/Document bheje
@app.on_message(filters.video | filters.document)
async def handle_video(client, message: Message):
    msg = await message.reply_text("⏳ Processing your video... Please wait bro!")
    
    # Video ko DB channel me forward karna (Backup ke liye)
    forwarded_msg = await message.forward(CHANNEL_ID)
    file_id = forwarded_msg.id # Database channel message ID
    
    # Render Server ka URL (tumhe Render se milega)
    # Abhi ke liye localhost ya app name
    RENDER_URL = os.environ.get("RENDER_URL", "URL_HERE") 
    
    stream_link = f"{RENDER_URL}/stream/{file_id}"
    
    await msg.edit_text(
        f"✅ **MeraStream Link Generated!**\n\n"
        f"🔗 `MeraStream://play?url={stream_link}`\n\n"
        f"(Ye link tumhare Android app me direct open hoga!)"
    )

# --- WEB SERVER (Streaming Logic) ---
routes = web.RouteTableDef()

@routes.get('/')
async def hello(request):
    return web.Response(text="MeraStream Server is Running! 🔥")

@routes.get('/stream/{msg_id}')
async def stream_video(request):
    msg_id = int(request.match_info['msg_id'])
    
    try:
        # DB channel se video get karna
        message = await app.get_messages(CHANNEL_ID, msg_id)
        if not message or not message.video:
            return web.Response(status=404, text="Video Not Found")

        # Telegram se file stream karna (Chunks me)
        # Note: Ye ek basic streaming response hai. 1GB+ ke liye advanced Range requests chahiye hoti hain.
        # Hum pehle isko chalu karte hain.
        
        file_size = message.video.file_size
        headers = {
            'Content-Type': message.video.mime_type,
            'Accept-Ranges': 'bytes',
        }
        
        # Generator for streaming
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
    # Bot aur Web Server dono ek sath chalenge
    await app.start()
    
    webapp = web.Application()
    webapp.add_routes(routes)
    runner = web.AppRunner(webapp)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    
    print("🔥 MeraStream Bot & Server is ALIVE!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(start_services())
