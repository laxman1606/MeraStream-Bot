import asyncio
# Magic: Event loop setup
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

import os
import re
from aiohttp import web
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

# Credentials
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "0"))
PORT = int(os.environ.get("PORT", 8080))

app = Client("MeraStreamBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- BOT COMMANDS ---
@app.on_message(filters.command("start"))
async def start_msg(client, message: Message):
    await message.reply_text("👋 Welcome to **MeraStream Pro**!\n\nMujhe 2GB tak ki koi bhi file bhejo, main makkhan ki tarah stream karunga!")

@app.on_message(filters.video | filters.document)
async def handle_video(client, message: Message):
    msg = await message.reply_text("⏳ Processing... Large files take a moment!")
    try:
        forwarded_msg = await message.forward(CHANNEL_ID)
        file_id = forwarded_msg.id 
        RENDER_URL = os.environ.get("RENDER_URL", "").strip().rstrip('/')
        watch_link = f"{RENDER_URL}/watch/{file_id}"
        
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("▶️ Open in App", url=watch_link)]])
        
        await msg.edit_text(
            f"✅ **MeraStream Link Ready!**\n\n🔗 {watch_link}\n\nAb badi files bhi smoothly chalengi!",
            reply_markup=keyboard
        )
    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")

# --- ADVANCED STREAMING SERVER (With Range Support) ---
routes = web.RouteTableDef()

@routes.get('/')
async def hello(request):
    return web.Response(text="MeraStream Engine is Running! 🚀")

@routes.get('/watch/{msg_id}')
async def watch_page(request):
    msg_id = request.match_info['msg_id']
    RENDER_URL = os.environ.get("RENDER_URL", "").strip().rstrip('/')
    app_link = f"MeraStream://play?url={RENDER_URL}/stream/{msg_id}"
    html = f"<html><body style='background:#000;color:#fff;text-align:center;padding-top:50px;'><h2>MeraStream Redirecting...</h2><script>window.location.href='{app_link}';</script><a href='{app_link}' style='color:red;'>Click to Open App Manually</a></body></html>"
    return web.Response(text=html, content_type='text/html')

@routes.get('/stream/{msg_id}')
async def stream_video(request):
    msg_id = int(request.match_info['msg_id'])
    range_header = request.headers.get('Range', 0)
    
    try:
        message = await app.get_messages(CHANNEL_ID, msg_id)
        file = message.video or message.document
        if not file: return web.Response(status=404)

        file_size = file.file_size
        start = 0
        end = file_size - 1

        # Range Header Parsing (Badi file ke liye zaroori)
        if range_header:
            match = re.search(r'bytes=(\d+)-(\d*)', range_header)
            if match:
                start = int(match.group(1))
                if match.group(2):
                    end = int(match.group(2))

        content_length = end - start + 1
        headers = {
            'Content-Type': file.mime_type or 'application/octet-stream',
            'Content-Range': f'bytes {start}-{end}/{file_size}',
            'Content-Length': str(content_length),
            'Accept-Ranges': 'bytes',
        }

        # Telegram se specific hissa (Range) stream karna
        response = web.StreamResponse(status=206, headers=headers)
        await response.prepare(request)

        async for chunk in app.stream_media(message, offset=start):
            await response.write(chunk)
            # Stop if we reached the requested end (important for performance)
            if response.prepared: 
                pass # aiohttp handles closing normally

        return response

    except Exception as e:
        print(f"Stream Error: {e}")
        return web.Response(status=500)

async def main():
    await app.start()
    webapp = web.Application()
    webapp.add_routes(routes)
    runner = web.AppRunner(webapp)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', PORT).start()
    print("🔥 Pro Server Live!")
    await idle()

if __name__ == "__main__":
    loop.run_until_complete(main())
