#!/usr/bin/env python3
"""
Telegram Webhook Setup Script - READY TO USE
This script helps you configure your Telegram bot to send images to your server

⚠️ UPDATE THIS: Change WEBHOOK_URL to your actual Railway domain
"""

import requests
import sys

# ✅ Your Telegram Bot Token (Already filled in)
TELEGRAM_BOT_TOKEN = "8260428040:AAHopZu53sdpM5-gPxa9nL2-Y2d7tsnOcRI"

# ⚠️ UPDATE THIS: Replace with your actual Railway URL
WEBHOOK_URL = "https://web-production-23072.up.railway.app/telegram-webhook"


def setup_webhook():
    """Configure Telegram bot webhook"""
    
    print(f"🤖 Bot Token: {TELEGRAM_BOT_TOKEN[:10]}...{TELEGRAM_BOT_TOKEN[-5:]}")
    print(f"🌐 Webhook URL: {WEBHOOK_URL}")
    print("\n📡 Setting up webhook...")
    
    # Set webhook
    set_webhook_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"
    payload = {"url": WEBHOOK_URL}
    
    try:
        response = requests.post(set_webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        if result.get("ok"):
            print("✅ Webhook set successfully!")
            print(f"   Description: {result.get('description', 'N/A')}")
            
            # Get webhook info to verify
            print("\n🔍 Verifying webhook...")
            info_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"
            info_response = requests.get(info_url, timeout=10)
            info_result = info_response.json()
            
            if info_result.get("ok"):
                webhook_info = info_result.get("result", {})
                print(f"   URL: {webhook_info.get('url')}")
                print(f"   Pending updates: {webhook_info.get('pending_update_count', 0)}")
                print(f"   Last error date: {webhook_info.get('last_error_date', 'None')}")
                print(f"   Last error message: {webhook_info.get('last_error_message', 'None')}")
            
            print("\n✨ Setup complete! Your bot is ready to receive images.")
            print("   Send a photo to your bot to test the integration.")
            return True
        else:
            print(f"❌ Failed to set webhook: {result.get('description', 'Unknown error')}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def delete_webhook():
    """Remove webhook configuration"""
    
    print("🗑️  Removing webhook...")
    
    delete_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook"
    
    try:
        response = requests.post(delete_url, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        if result.get("ok"):
            print("✅ Webhook removed successfully!")
            return True
        else:
            print(f"❌ Failed to remove webhook: {result.get('description', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def get_webhook_info():
    """Get current webhook information"""
    
    print("🔍 Getting webhook info...")
    
    info_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"
    
    try:
        response = requests.get(info_url, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        if result.get("ok"):
            webhook_info = result.get("result", {})
            print("\n📋 Webhook Information:")
            print(f"   URL: {webhook_info.get('url', 'Not set')}")
            print(f"   Has custom certificate: {webhook_info.get('has_custom_certificate', False)}")
            print(f"   Pending updates: {webhook_info.get('pending_update_count', 0)}")
            print(f"   Max connections: {webhook_info.get('max_connections', 40)}")
            print(f"   Allowed updates: {webhook_info.get('allowed_updates', 'All')}")
            
            if webhook_info.get('last_error_date'):
                print(f"   ⚠️  Last error date: {webhook_info.get('last_error_date')}")
                print(f"   ⚠️  Last error message: {webhook_info.get('last_error_message', 'N/A')}")
            else:
                print("   ✅ No errors")
            
            return True
        else:
            print(f"❌ Failed to get webhook info: {result.get('description', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Telegram Webhook Setup for Smart Parking System")
    print("=" * 60)
    print()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command == "delete":
            delete_webhook()
        elif command == "info":
            get_webhook_info()
        elif command == "setup":
            setup_webhook()
        else:
            print("❌ Unknown command. Use: setup, delete, or info")
            print("\nUsage:")
            print("  python setup_telegram_webhook.py setup   - Setup webhook")
            print("  python setup_telegram_webhook.py info    - Get webhook info")
            print("  python setup_telegram_webhook.py delete  - Delete webhook")
    else:
        # Default: setup webhook
        setup_webhook()
    
    print("\n" + "=" * 60)
