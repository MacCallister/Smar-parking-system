#!/usr/bin/env python3
"""
Test script to verify Telegram integration and image processing
"""

import os
import sys
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def test_telegram_download():
    """Test downloading an image from Telegram"""
    print("🧪 Testing Telegram Image Download")
    print("=" * 60)
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not bot_token:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN not set")
        return False
    
    # You need to get a real file_id by sending an image to your bot
    # and checking the update or your server logs
    file_id = input("\n📷 Enter a Telegram file_id to test (or press Enter to skip): ").strip()
    
    if not file_id:
        print("\n⏭️  Skipping download test (no file_id provided)")
        print("   To get a file_id:")
        print("   1. Send an image to your bot")
        print("   2. Check your server logs or use getUpdates API")
        return True
    
    try:
        # Get file info
        print(f"\n📡 Fetching file info for: {file_id[:20]}...")
        get_file_url = f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}"
        
        response = requests.get(get_file_url, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        
        if not result.get("ok"):
            print(f"❌ Error: {result.get('description', 'Unknown error')}")
            return False
        
        file_path = result["result"]["file_path"]
        file_size = result["result"].get("file_size", "Unknown")
        
        print(f"✅ File info retrieved:")
        print(f"   Path: {file_path}")
        print(f"   Size: {file_size} bytes")
        
        # Download file
        download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
        print(f"\n⬇️  Downloading image...")
        
        img_response = requests.get(download_url, timeout=30)
        img_response.raise_for_status()
        
        img_bytes = img_response.content
        print(f"✅ Downloaded {len(img_bytes)} bytes")
        
        # Save test file
        test_file = "test_telegram_image.jpg"
        with open(test_file, "wb") as f:
            f.write(img_bytes)
        
        print(f"✅ Saved to: {test_file}")
        print("\n✨ Telegram download test PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        return False


def test_upload_endpoint():
    """Test the /upload endpoint with telegram_file_id"""
    print("\n🧪 Testing /upload Endpoint")
    print("=" * 60)
    
    server_url = os.getenv("WEBHOOK_URL")
    if server_url:
        # Extract base URL from webhook URL
        server_url = server_url.replace("/telegram-webhook", "")
    else:
        server_url = input("\n🌐 Enter your server URL (e.g., https://your-app.railway.app): ").strip()
    
    if not server_url:
        print("⏭️  Skipping endpoint test (no URL provided)")
        return True
    
    # Test GET request first
    try:
        print(f"\n📡 Testing GET {server_url}/upload")
        response = requests.get(f"{server_url}/upload", timeout=10)
        
        if response.status_code == 200:
            print("✅ GET request successful")
            print(f"   Response: {response.json()}")
        else:
            print(f"⚠️  GET returned {response.status_code}")
    except Exception as e:
        print(f"❌ GET request failed: {e}")
        return False
    
    # Test POST with file_id
    file_id = input("\n📷 Enter a Telegram file_id to test POST (or press Enter to skip): ").strip()
    
    if not file_id:
        print("⏭️  Skipping POST test")
        return True
    
    try:
        print(f"\n📡 Testing POST {server_url}/upload")
        payload = {
            "telegram_file_id": file_id,
            "camera_id": "TEST_CAM"
        }
        
        response = requests.post(
            f"{server_url}/upload",
            json=payload,
            timeout=60
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ POST request successful")
            print(f"   Status: {result.get('status')}")
            print(f"   Scene URL: {result.get('scene_url', 'N/A')}")
            print(f"   Plates detected: {len(result.get('plates', []))}")
            
            if result.get('plates'):
                for i, plate in enumerate(result['plates'], 1):
                    print(f"\n   Plate {i}:")
                    print(f"     Text: {plate.get('text')}")
                    print(f"     Confidence: {plate.get('confidence', 0):.2f}")
                    print(f"     URL: {plate.get('plate_url', 'N/A')}")
            
            print("\n✨ Upload endpoint test PASSED!")
            return True
        else:
            print(f"❌ POST returned {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ POST request failed: {e}")
        return False


def test_webhook_info():
    """Check current webhook configuration"""
    print("\n🧪 Testing Webhook Configuration")
    print("=" * 60)
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not bot_token:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN not set")
        return False
    
    try:
        info_url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
        response = requests.get(info_url, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("ok"):
            webhook_info = result.get("result", {})
            
            print("📋 Current Webhook Configuration:")
            print(f"   URL: {webhook_info.get('url', 'Not set')}")
            print(f"   Pending updates: {webhook_info.get('pending_update_count', 0)}")
            
            if webhook_info.get('url'):
                print("   ✅ Webhook is configured")
                
                if webhook_info.get('last_error_date'):
                    print(f"   ⚠️  Last error: {webhook_info.get('last_error_message', 'N/A')}")
                else:
                    print("   ✅ No errors")
                
                return True
            else:
                print("   ⚠️  Webhook is not set up")
                print("\n   Run: python setup_telegram_webhook.py setup")
                return False
        else:
            print(f"❌ Error: {result.get('description', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def main():
    print("=" * 60)
    print("🚀 Smart Parking System - Telegram Integration Test")
    print("=" * 60)
    
    # Check environment variables
    print("\n📋 Checking Environment Variables...")
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    webhook_url = os.getenv("WEBHOOK_URL")
    supabase_url = os.getenv("SUPABASE_URL")
    
    if bot_token:
        print(f"   ✅ TELEGRAM_BOT_TOKEN: {bot_token[:10]}...{bot_token[-5:]}")
    else:
        print("   ❌ TELEGRAM_BOT_TOKEN: Not set")
    
    if webhook_url:
        print(f"   ✅ WEBHOOK_URL: {webhook_url}")
    else:
        print("   ⚠️  WEBHOOK_URL: Not set")
    
    if supabase_url:
        print(f"   ✅ SUPABASE_URL: {supabase_url}")
    else:
        print("   ❌ SUPABASE_URL: Not set")
    
    # Run tests
    tests = [
        ("Webhook Configuration", test_webhook_info),
        ("Telegram Image Download", test_telegram_download),
        ("Upload Endpoint", test_upload_endpoint),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {status}: {test_name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print(f"\n   Total: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n✨ All tests passed! Your integration is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Please review the errors above.")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
