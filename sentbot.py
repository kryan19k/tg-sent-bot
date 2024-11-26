from telegram.ext import Application, CommandHandler
from aiohttp import web
import json
import asyncio
from dotenv import load_dotenv
import os
import logging
import hmac
import hashlib
import sys
from datetime import datetime
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),  # Log to file
        logging.StreamHandler(sys.stdout)  # Log to console
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHANNEL_ID')
WEBHOOK_SECRET = os.getenv('GITHUB_WEBHOOK_SECRET')

# Store application globally
app = None

async def send_message(text):
    await app.bot.send_message(chat_id=CHAT_ID, text=text)

async def handle_webhook(request):
    logger.info(f"Received webhook request: {request.path}")
    try:
        # Verify GitHub webhook signature
        signature = request.headers.get('X-Hub-Signature-256')
        if not signature:
            logger.warning("No signature header found")
            return web.Response(text="No signature", status=403)

        raw_data = await request.read()
        if WEBHOOK_SECRET:
            expected_signature = 'sha256=' + hmac.new(
                WEBHOOK_SECRET.encode(),
                raw_data,
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                logger.warning("Invalid signature")
                return web.Response(text="Invalid signature", status=403)

        data = json.loads(raw_data)
        logger.info(f"Webhook data: {data}")
        
        if 'commits' in data:
            repo_name = data['repository']['name']
            pusher = data['pusher']['name']
            commits = data['commits']
            
            message = f"🔵 New push to {repo_name} by {pusher}\n\n"
            for commit in commits:
                message += f"📝 {commit['message']}\n"
            
            await send_message(message)
            return web.Response(text="OK")
        return web.Response(text="No commits found")
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return web.Response(text=str(e), status=500)

async def handle_root(request):
    return web.Response(text="Bot webhook server is running!")

async def start(update, context):
    await update.message.reply_text('Bot is running!')

async def run_webhook_server():
    webhook_app = web.Application()
    webhook_app.router.add_post('/webhook', handle_webhook)
    webhook_app.router.add_get('/', handle_root)  # Add root handler
    
    runner = web.AppRunner(webhook_app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()
    
    logger.info("Webhook server running on http://localhost:8080")
    logger.info(f"Ngrok URL should be configured to /webhook endpoint")
    
    # Keep the server running
    while True:
        await asyncio.sleep(1)

async def error_handler(update, context):
    """Log Errors caused by Updates."""
    logger.error(f"Update {update} caused error {context.error}")
    error_msg = f"""
⚠️ Bot Error Report
Time: {datetime.now()}
Error: {str(context.error)}
Traceback: {traceback.format_exc()}
    """
    # Optionally send error reports to an admin
    if os.getenv('ADMIN_CHAT_ID'):
        await app.bot.send_message(
            chat_id=os.getenv('ADMIN_CHAT_ID'),
            text=error_msg
        )

async def main():
    global app
    try:
        app = Application.builder().token(TOKEN).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", start))
        app.add_error_handler(error_handler)
        
        # Start both the bot and webhook server
        async with app:
            await app.start()
            await run_webhook_server()
            
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")