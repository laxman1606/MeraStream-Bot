import asyncio
# Magic: Event loop setup for Render
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

import os
import re
from aiohttp import web
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

# Credentials (Environment Variables)
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "0"))
PORT = int(os.environ.get("PORT", 8080))

app = Client("MeraStreamBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- BOT COMMANDS ---
@app.on_message(filters.command("start"))
async def start_msg(client, message: Message):
    await message.reply_text(
        "👋 **Welcome to MeraStream Pro Engine!**\n\n"
        "Mujhe koi bhi badi video file bhejo, main makkhan ki tarah streaming link bana dunga.\n\n"
        "✅ 2GB File Support\n"
        "✅ Fast Seeking (Range Support)\n"
        "✅ Auto App Redirect"
    )

@app.on_message(filters.video | filters.document)
async def handle_video(client, message: Message):
    msg = await message.reply_text("⏳ Processing your large file... Please wait!")
    try:
        # DB Channel me forward karna backup ke liye
        forwarded_msg = await message.forward(CHANNEL_ID)
        file_id = forwarded_msg.id 
        
        RENDER_URL = os.environ.get("RENDER_URL", "").strip().rstrip('/')
        watch_link = f"{RENDER_URL}/watch/{file_id}"
        
        # Professional Inline Button
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ Play in MeraStream App", url=watch_link)]
        ])
        
        file_name = message.video.file_name if message.video else message.document.file_name
        
        await msg.edit_text(
            f"🎬 **File Name:** `{file_name}`\n\n"
            f"🔗 **Streaming Link:** {watch_link}\n\n"
            f"🚀 _Click the button below to open directly in your Android App!_",
            reply_markup=keyboard
        )
    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")

# --- WEB SERVER LOGIC ---
routes = web.RouteTableDef()

@routes.get('/')
async def hello(request):
    return web.Response(text="MeraStream Pro Engine is ALIVE! 🚀", content_type='text/plain')

# ✨ NAYA SMART REDIRECT PAGE ✨
@routes.get('/watch/{msg_id}')
async def watch_page(request):
    msg_id = request.match_info['msg_id']
    RENDER_URL = os.environ.get("RENDER_URL", "").strip().rstrip('/')
    
    # Direct Stream Link (For Player)
    stream_link = f"{RENDER_URL}/stream/{msg_id}"
    # Deep Link (To open App)
    app_deep_link = f"MeraStream://play?url={stream_link}"
    
    # Full Professional HTML with Meta Tags for Telegram Preview
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>MeraStream - Opening Video</title>
        
        <!-- Telegram/Social Media Preview Tags -->
        <meta property="og:title" content="▶️ Play Video in MeraStream">
        <meta property="og:description" content="Stream high-quality video directly in your app without downloading.">
        <meta property="og:image" content="https://i.imgur.com/8m5uR6y.png"> <!-- Yahan apna logo link daal sakte ho -->
        <meta property="og:type" content="video.other">
        
        <style>
            body {{
                background-color: #0f0f0f;
                color: #ffffff;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
            }}
            .loader {{
                border: 4px solid #f3f3f3;
                border-top: 4px solid #e50914;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin-bottom: 20px;
            }}
            @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
            .btn {{
                background-color: #e50914;
                color: white;
                padding: 12px 24px;
                text-decoration: none;
                border-radius: 8px;
                font-weight: bold;
                margin-top: 20px;
                transition: 0.3s;
            }}
            .btn:hover {{ background-color: #b20710; }}
            h2 {{ margin-bottom: 10px; }}
            p {{ color: #aaa; }}
        </style>
    </head>
    <body>
        <div class="loader"></div>
        <h2>Opening MeraStream App...</h2>
        <p>If the app doesn't open automatically, click the button below.</p>
        <a href="{app_deep_link}" class="btn">OPEN IN APP</a>

        <script>
            // Auto redirect logic
            setTimeout(function() {{
                window.location.href = "{app_deep_link}";
            }}, 500);
        </script>
    </body>
    </html>
    """
    return web.Response(text=html_content, content_type='text/html')

# 🚀 ADVANCED STREAMING ENGINE (Range/Seek Support for 1GB+)
@routes.get('/stream/{msg_id}')
async def stream_video(request):
    msg_id = int(request.match_info['msg_id'])
    range_header = request.headers.get('Range', None)
    
    try:
        message = await app.get_messages(CHANNEL_ID, msg_id)
        file = message.video or message.document
        if not file:
            return web.Response(status=404, text="File Not Found")

        file_size = file.file_size
        start = 0
        end = file_size - 1

        # Range Parsing logic
        if range_header:
            match = re.search(r'bytes=(\d+)-(\d*)', range_header)
            if match:
                start = int(match.group(1))
                if match.group(2):
                    end = int(match.group(2))

        content_length = end - start + 1
        headers = {
            'Content-Type': file.mime_type or 'video/mp4',
            'Content-Range': f'bytes {start}-{end}/{file_size}',
            'Content-Length': str(content_length),
            'Accept-Ranges': 'bytes',
        }

        # Status 206 is crucial for seeking in large videos
        response = web.StreamResponse(status=206, headers=headers)
        await response.prepare(request)

        # Pyrogram stream_media with offset
        async for chunk in app.stream_media(message, offset=start):
            await response.write(chunk)

        return response

    except Exception as e:
        print(f"Streaming Error: {e}")
        return web.Response(status=500, text="Internal Server Error")

# --- STARTUP ---
async def main():
    await app.start()
    webapp = web.Application()
    webapp.add_routes(routes)
    runner = web.AppRunner(webapp)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"🔥 MeraStream Engine is LIVE on Port {PORT}")
    await idle()
    await app.stop()

if __name__ == "__main__":
    loop.run_until_complete(main())
