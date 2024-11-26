from http.client import HTTPResponse
from telegram.ext import Application
import json
import hmac
import hashlib
import os
from datetime import datetime
from dotenv import load_dotenv
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHANNEL_ID')
WEBHOOK_SECRET = os.getenv('GITHUB_WEBHOOK_SECRET')

async def send_message(text: str):
    app = Application.builder().token(TOKEN).build()
    async with app:
        await app.bot.send_message(chat_id=CHAT_ID, text=text)

def create_response(status_code: int, body: str) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "body": body,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "X-Hub-Signature-256, Content-Type"
        }
    }

# This is the main handler that Vercel will call
async def main(request):
    # Handle OPTIONS request for CORS
    if request.method == "OPTIONS":
        return create_response(200, "OK")

    if request.method != "POST":
        return create_response(405, json.dumps({"error": "Method not allowed"}))

    try:
        # Get the raw body
        body = await request.body()
        
        # Verify GitHub webhook signature
        signature = request.headers.get('X-Hub-Signature-256')
        if not signature:
            return create_response(403, json.dumps({"error": "No signature"}))

        if WEBHOOK_SECRET:
            expected_signature = 'sha256=' + hmac.new(
                WEBHOOK_SECRET.encode(),
                body,
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                return create_response(403, json.dumps({"error": "Invalid signature"}))

        # Parse the JSON body
        data = json.loads(body)
        logger.info(f"Webhook data: {data}")
        
        if 'commits' in data:
            repo_name = data['repository']['name']
            pusher = data['pusher']['name']
            commits = data['commits']
            
            message = f"🔵 New push to {repo_name} by {pusher}\n\n"
            for commit in commits:
                message += f"📝 {commit['message']}\n"
            
            await send_message(message)
            return create_response(200, json.dumps({"status": "success"}))
            
        return create_response(200, json.dumps({"status": "no commits found"}))

    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return create_response(500, json.dumps({"error": str(e)}))

# Vercel serverless handler
def handler(request):
    return main(request) 