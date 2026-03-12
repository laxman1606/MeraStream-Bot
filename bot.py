import asyncio
# MAGIC TRICK: Pyrogram import hone se pehle Event Loop bana do
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

import os
import re
from aiohttp import web
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

# Credentials (Environment Variables)
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
    await message.reply_text("👋 Welcome to **MeraStream Pro Bot**!\n\nMujhe koi bhi badi video file (1GB+) bhejo, mai tumhe Direct Streaming Link dunga!")

@app.on_message(filters.video | filters.document)
async def handle_video(client, message: Message):
    if CHANNEL_ID == 0:
        await message.reply_text("❌ Error: CHANNEL_ID set nahi hai Render me!")
        return

    msg = await message.reply_text("⏳ Processing your video... Please wait bro!")
    
    try:
        # DB channel me forward karna
        forwarded_msg = await message.forward(CHANNEL_ID)
        file_id = forwarded_msg.id 
        
        RENDER_URL = os.environ.get("RENDER_URL", "").strip().rstrip('/')
            
        watch_link = f"{RENDER_URL}/watch/{file_id}"
        
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("▶️ Open in MeraStream App", url=watch_link)],
                [InlineKeyboardButton("🔗 Share Link", switch_inline_query=watch_link)]
            ]
        )
        
        # File Name aur Size nikalna
        file = message.video or message.document
        file_name = getattr(file, "file_name", None) or "MeraStream_Video.mp4"
        file_size = getattr(file, "file_size", 0)

        if file_size < 1024 * 1024 * 1024:
            file_size_str = f"{file_size / (1024 * 1024):.2f} MB"
        else:
            file_size_str = f"{file_size / (1024 * 1024 * 1024):.2f} GB"
        
        await msg.edit_text(
            f"✅ **MeraStream Link Generated!**\n\n"
            f"🎬 **Name:** `{file_name}`\n"
            f"📦 **Size:** `{file_size_str}`\n\n"
            f"🔗 **Link:** {watch_link}\n\n"
            f"👇 Click button below to stream directly in the App!",
            reply_markup=keyboard,
            disable_web_page_preview=False
        )
    except Exception as e:
        await msg.edit_text(f"❌ Error aagaya bro: {e}")

# ==========================================
# 🌐 WEB SERVER (STREAMING & REDIRECT)
# ==========================================

routes = web.RouteTableDef()

@routes.get('/')
async def hello(request):
    return web.Response(text="✅ MeraStream Server is Running Perfectly! 🔥")

@routes.get('/thumb/{msg_id}.jpg')
async def get_thumb(request):
    msg_id = int(request.match_info['msg_id'])
    try:
        message = await app.get_messages(CHANNEL_ID, msg_id)
        file = message.video or message.document
        if file and getattr(file, "thumbs", None):
            thumb_data = await app.download_media(file.thumbs[0].file_id, in_memory=True)
            return web.Response(body=thumb_data.getvalue(), content_type='image/jpeg')
    except Exception:
        pass
    raise web.HTTPFound('https://i.imgur.com/your-fallback-logo.jpg')

@routes.get('/watch/{msg_id}')
async def watch_page(request):
    msg_id = request.match_info['msg_id']
    RENDER_URL = os.environ.get("RENDER_URL", "").strip().rstrip('/')
    
    stream_link = f"{RENDER_URL}/stream/{msg_id}"
    intent_uri = f"intent://play?url={stream_link}#Intent;scheme=MeraStream;package=com.merastream.app;end;"
    app_deep_link = f"MeraStream://play?url={stream_link}"
    thumb_link = f"{RENDER_URL}/thumb/{msg_id}.jpg"
    
    html_page = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>MeraStream - Watch Video</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="twitter:card" content="summary_large_image">
        <meta property="og:title" content="▶️ Play Video in MeraStream">
        <meta property="og:description" content="Click to stream this video directly in high quality.">
        <meta property="og:image" content="{thumb_link}">
        <style>
            body {{ background-color: #121212; color: white; font-family: Arial, sans-serif; text-align: center; padding-top: 15%; }}
            .loader {{ border: 4px solid #333; border-top: 4px solid #E50914; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto 20px auto; }}
            @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
            .btn {{ background-color: #E50914; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-size: 18px; font-weight: bold; display: none; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="loader"></div>
        <h2>Opening App...</h2>
        <p>You are being redirected securely.</p>
        <a id="autoLink" href="{app_deep_link}" class="btn">CLICK TO OPEN APP</a>
        <script>
            window.onload = function() {{
                window.location.href = "{intent_uri}";
                setTimeout(function() {{
                    document.getElementById("autoLink").style.display = "inline-block";
                }}, 1500);
            }};
        </script>
    </body>
    </html>
    """
    return web.Response(text=html_page, content_type='text/html')

# ==========================================
# 🚀 THE ULTIMATE "BYTE-SLICER" STREAMING FIX
# ==========================================
@routes.route('*', '/stream/{msg_id}')
async def stream_video(request):
    msg_id = int(request.match_info['msg_id'])
    
    try:
        message = await app.get_messages(CHANNEL_ID, msg_id)
        if not message or not (message.video or message.document):
            return web.Response(status=404, text="Video Not Found")

        file = message.video or message.document
        file_size = file.file_size
        file_name = getattr(file, "file_name", "MeraStream_Video.mp4")
        mime_type = file.mime_type or 'video/mp4'

        headers = {
            'Content-Type': mime_type,
            'Accept-Ranges': 'bytes',
            'Content-Disposition': f'inline; filename="{file_name}"'
        }

        # Handle HEAD request for ExoPlayer and DownloadManager
        if request.method == 'HEAD':
            headers['Content-Length'] = str(file_size)
            return web.Response(status=200, headers=headers)

        range_header = request.headers.get('Range')
        status_code = 200

        if range_header:
            match = re.search(r'bytes=(\d+)-(\d*)', range_header)
            start = int(match.group(1)) if match else 0
            # ExoPlayer kayi baar end byte nahi bhejta, toh hum file_size-1 maante hain
            end = int(match.group(2)) if match and match.group(2) else file_size - 1

            if start >= file_size:
                headers['Content-Range'] = f'bytes */{file_size}'
                return web.Response(status=416, headers=headers)

            length = end - start + 1
            headers['Content-Range'] = f'bytes {start}-{end}/{file_size}'
            headers['Content-Length'] = str(length)
            status_code = 206
        else:
            start = 0
            end = file_size - 1
            length = file_size
            headers['Content-Length'] = str(length)

        response = web.StreamResponse(status=status_code, headers=headers)
        await response.prepare(request)

        # ⚡ MANUAL BYTE SLICING ALGORITHM ⚡
        # ExoPlayer jitna byte maangega, EXACTLY utna hi bheja jayega. Ek byte extra nahi!
        yielded_bytes = 0
        try:
            async for chunk in app.stream_media(message, offset=start):
                chunk_size = len(chunk)
                
                # Agar chunk bhejne se length limit cross ho rahi hai, toh extra data kaat do (Slice)
                if yielded_bytes + chunk_size > length:
                    remaining_bytes = length - yielded_bytes
                    await response.write(chunk[:remaining_bytes])
                    break # Exact data bhej diya, ab loop band karo
                
                await response.write(chunk)
                yielded_bytes += chunk_size
                
        except Exception:
            # Player ne aage/peeche bhagaya, toh connection cancel hoga. Isko chup-chap ignore karna hai.
            pass

        return response

    except Exception as e:
        print(f"Stream error: {e}")
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
