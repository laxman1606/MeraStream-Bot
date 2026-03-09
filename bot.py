import asyncio
# MAGIC TRICK: Pyrogram import hone se pehle Event Loop bana do
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

import os
from aiohttp import web
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

# Tumhare environment variables ko safely extract karna
API_ID_STR = os.environ.get("API_ID", "").strip()
API_HASH = os.environ.get("API_HASH", "").strip()
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()

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

# Pyrogram Client Setup
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
        await message.reply_text("❌ Error: CHANNEL_ID set nahi hai Render me!")
        return

    msg = await message.reply_text("⏳ Processing your video... Please wait bro!")
    
    try:
        # Video ko DB channel me forward karna
        forwarded_msg = await message.forward(CHANNEL_ID)
        file_id = forwarded_msg.id 
        
        RENDER_URL = os.environ.get("RENDER_URL", "").strip()
        if RENDER_URL.endswith('/'):
            RENDER_URL = RENDER_URL[:-1]
            
        # HTTP link banana taaki Blue color aaye aur Button lag sake
        watch_link = f"{RENDER_URL}/watch/{file_id}"
        
        # Professional Telegram Button
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("▶️ Play in MeraStream", url=watch_link)],
                [InlineKeyboardButton("🔗 Share Link", switch_inline_query=watch_link)]
            ]
        )
        
        # File Size Calculate karna
        file_size_mb = 0
        if message.video:
            file_size_mb = message.video.file_size / (1024 * 1024)
        elif message.document:
            file_size_mb = message.document.file_size / (1024 * 1024)
        
        await msg.edit_text(
            f"✅ **MeraStream Link Generated!**\n\n"
            f"🎬 **File ID:** `{file_id}`\n"
            f"📦 **Size:** `{file_size_mb:.2f} MB`\n\n"
            f"🔗 **Link:** {watch_link}\n\n"
            f"👇 Click button below to stream directly in the App!",
            reply_markup=keyboard,
            disable_web_page_preview=False
        )
    except Exception as e:
        await msg.edit_text(f"❌ Error aagaya bro: {e}")

# ==========================================
# 🌐 WEB SERVER (STREAMING & REDIRECT LOGIC)
# ==========================================

routes = web.RouteTableDef()

@routes.get('/')
async def hello(request):
    return web.Response(text="✅ MeraStream Server is Running Perfectly! 🔥")

# ==========================================
# 🔥 AGGRESSIVE AUTO-REDIRECT LOGIC
# ==========================================
@routes.get('/watch/{msg_id}')
async def watch_page(request):
    msg_id = request.match_info['msg_id']
    RENDER_URL = os.environ.get("RENDER_URL", "").strip().rstrip('/')
    
    stream_link = f"{RENDER_URL}/stream/{msg_id}"
    
    # 💥 Android Intent URL: Ye direct OS ko force karta hai app kholne ke liye
    # (Dhyan rakhna: package=com.merastream.app wahi hona chahiye jo Android studio me tha)
    intent_link = f"intent://play?url={stream_link}#Intent;scheme=MeraStream;package=com.merastream.app;end"
    
    html_page = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>MeraStream - Opening...</title>
        <style>
            body {{ background-color: #000000; color: white; font-family: sans-serif; text-align: center; margin-top: 40%; }}
            .loader {{ border: 4px solid #333; border-top: 4px solid #E50914; border-radius: 50%; width: 50px; height: 50px; animation: spin 1s linear infinite; margin: 0 auto 20px auto; }}
            @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
            .btn {{ background-color: #E50914; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block; margin-top: 20px; font-size: 16px; border: none; }}
        </style>
    </head>
    <body>
        <div class="loader"></div>
        <h2>Opening MeraStream App... 🚀</h2>
        <p style="color: #888; font-size: 14px;">Please wait while we redirect you...</p>
        
        <!-- Hidden button for JS auto-click bypass -->
        <a id="autoClickBtn" href="{intent_link}" style="display:none;">Auto Click</a>
        
        <!-- Manual button just in case strict browsers block everything -->
        <a href="{intent_link}" class="btn">▶️ Tap here if App doesn't open</a>

        <script>
            // 1. Direct Intent Redirect (Works on most Android devices)
            setTimeout(function() {{
                window.location.href = "{intent_link}";
            }}, 100);

            // 2. JS Auto-Click Simulation (Bypasses Telegram In-App Browser Blocks)
            setTimeout(function() {{
                document.getElementById('autoClickBtn').click();
            }}, 400);
            
            // 3. Fallback replace method
            setTimeout(function() {{
                window.location.replace("{intent_link}");
            }}, 800);
        </script>
    </body>
    </html>
    """
    return web.Response(text=html_page, content_type='text/html')

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
# 🚀 MAIN FUNCTION
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
        return

    print("🔥 Everything is running. Waiting for messages...")
    await idle()
    
    print("🛑 Stopping services...")
    await app.stop()
    await runner.cleanup()

if __name__ == "__main__":
    loop.run_until_complete(main())
