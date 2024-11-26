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

def handle_webhook(request):
    try:
        # Get request body
        body = request.body.decode()
        
        # Verify GitHub webhook signature
        signature = request.headers.get('X-Hub-Signature-256')
        if not signature:
            return {
                "statusCode": 403,
                "body": json.dumps({"error": "No signature"}),
                "headers": {"Content-Type": "application/json"}
            }

        if WEBHOOK_SECRET:
            expected_signature = 'sha256=' + hmac.new(
                WEBHOOK_SECRET.encode(),
                body.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                return {
                    "statusCode": 403,
                    "body": json.dumps({"error": "Invalid signature"}),
                    "headers": {"Content-Type": "application/json"}
                }

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
            
            # Note: In serverless, we can't use async/await directly
            # We'll need to use a different approach for sending messages
            app = Application.builder().token(TOKEN).build()
            app.bot.send_message(chat_id=CHAT_ID, text=message)
            
            return {
                "statusCode": 200,
                "body": json.dumps({"status": "success"}),
                "headers": {"Content-Type": "application/json"}
            }
            
        return {
            "statusCode": 200,
            "body": json.dumps({"status": "no commits found"}),
            "headers": {"Content-Type": "application/json"}
        }

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": {"Content-Type": "application/json"}
        }

def handler(request):
    if request.method == "OPTIONS":
        return {
            "statusCode": 200,
            "body": "OK",
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "X-Hub-Signature-256, Content-Type"
            }
        }
    
    if request.method == "POST":
        return handle_webhook(request)
    
    return {
        "statusCode": 405,
        "body": json.dumps({"error": "Method not allowed"}),
        "headers": {"Content-Type": "application/json"}
    } 