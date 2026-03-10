import asyncio
# Magic: Event loop setup for Render
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

import os
import re
import urllib.parse  # NAYA: URL ko safe banane ke liye
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
        "👋 **Welcome to MeraStream Pro!**\n\n"
        "Mujhe koi bhi video bhejo, main uska HD Streaming Link aur Thumbnail generate karunga!"
    )

@app.on_message(filters.video | filters.document)
async def handle_video(client, message: Message):
    msg = await message.reply_text("⏳ Processing your file... Please wait!")
    try:
        # DB Channel me forward karna backup ke liye
        forwarded_msg = await message.forward(CHANNEL_ID)
        file_id = forwarded_msg.id 
        
        RENDER_URL = os.environ.get("RENDER_URL", "").strip().rstrip('/')
        watch_link = f"{RENDER_URL}/watch/{file_id}"
        
        # File Name aur Size nikalna
        file = message.video or message.document
        file_name = getattr(file, "file_name", None) or "MeraStream_Video.mp4"
        file_size = getattr(file, "file_size", 0)
        
        if file_size < 1024 * 1024 * 1024:
            size_str = f"{file_size / (1024 * 1024):.2f} MB"
        else:
            size_str = f"{file_size / (1024 * 1024 * 1024):.2f} GB"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ Play in MeraStream App", url=watch_link)]
        ])
        
        await msg.edit_text(
            f"🎬 **File Name:** `{file_name}`\n"
            f"📦 **Size:** `{size_str}`\n\n"
            f"🔗 **Streaming Link:** {watch_link}\n\n"
            f"🚀 _Click the link or button below to stream directly!_",
            reply_markup=keyboard
        )
    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")

# --- WEB SERVER LOGIC ---
routes = web.RouteTableDef()

@routes.get('/')
async def hello(request):
    return web.Response(text="MeraStream Engine is ALIVE! 🚀", content_type='text/plain')

# THUMBNAIL ROUTE
@routes.get('/thumb/{msg_id}.jpg')
async def get_thumb(request):
    msg_id = int(request.match_info['msg_id'])
    try:
        message = await app.get_messages(CHANNEL_ID, msg_id)
        file = message.video or message.document
        if file and getattr(file, "thumbs", None):
            thumb_data = await app.download_media(file.thumbs[0].file_id, in_memory=True)
            return web.Response(body=thumb_data.getvalue(), content_type='image/jpeg')
    except Exception as e:
        pass
    raise web.HTTPFound('https://i.imgur.com/your-fallback-logo.jpg')

# ✨ SMART REDIRECT PAGE (THE ULTIMATE FIX) ✨
@routes.get('/watch/{msg_id}')
async def watch_page(request):
    msg_id = request.match_info['msg_id']
    RENDER_URL = os.environ.get("RENDER_URL", "").strip().rstrip('/')
    
    stream_link = f"{RENDER_URL}/stream/{msg_id}"
    
    # 🔥 PRO TRICK: URL ko encode kiya taaki Android App confuse na ho
    encoded_stream_link = urllib.parse.quote(stream_link, safe='')
    
    # INTENT URI: Ye Telegram browser ko force karta hai app auto-open karne ke liye
    # (Apna package name com.merastream.app hi hai na, confirm kar lena)
    intent_uri = f"intent://play?url={encoded_stream_link}#Intent;scheme=MeraStream;package=com.merastream.app;end;"
    
    app_deep_link = f"MeraStream://play?url={stream_link}"
    thumb_link = f"{RENDER_URL}/thumb/{msg_id}.jpg"
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>MeraStream - Watch Video</title>
        
        <meta name="twitter:card" content="summary_large_image">
        <meta property="og:title" content="▶️ Watch Video in MeraStream">
        <meta property="og:description" content="Click here to stream this video in high quality inside the app.">
        <meta property="og:image" content="{thumb_link}">
        
        <style>
            body {{
                background-color: #121212; color: #ffffff; font-family: Arial, sans-serif;
                display: flex; flex-direction: column; align-items: center; justify-content: center;
                height: 100vh; margin: 0; text-align: center;
            }}
            .loader {{
                border: 4px solid #333; border-top: 4px solid #e50914; border-radius: 50%;
                width: 50px; height: 50px; animation: spin 1s linear infinite; margin-bottom: 20px;
            }}
            @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
            .btn {{
                background-color: #e50914; color: white; padding: 15px 30px; text-decoration: none;
                border-radius: 8px; font-weight: bold; font-size: 18px; margin-top: 20px; display: none;
            }}
        </style>
    </head>
    <body>
        <div class="loader"></div>
        <h2>Opening App Automatically...</h2>
        <p>You are being redirected securely.</p>
        
        <!-- Button ab chupa hua hai (display: none), sirf emergency me dikhega -->
        <a id="autoLink" href="{intent_uri}" class="btn">CLICK TO OPEN APP</a>

        <script>
            window.onload = function() {{
                // 1. DIRECT AUTO-OPEN (Bypasses Telegram blocks)
                window.location.href = "{intent_uri}";
                
                // 2. Agar phir bhi 2 second me app na khule, toh Manual Button dikha do
                setTimeout(function() {{
                    document.getElementById("autoLink").style.display = "inline-block";
                    document.getElementById("autoLink").href = "{app_deep_link}"; // Fallback link
                }}, 2000);
            }};
        </script>
    </body>
    </html>
    """
    return web.Response(text=html_content, content_type='text/html')

# STREAMING ENGINE (RANGE SUPPORT)
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

        response = web.StreamResponse(status=206, headers=headers)
        await response.prepare(request)

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
