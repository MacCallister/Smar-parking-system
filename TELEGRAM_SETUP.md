# Telegram Integration Setup Guide

This guide explains how to integrate your Smart Parking System with Telegram to automatically process images sent to your bot.

## Overview

The system now supports receiving images directly from Telegram. When a user sends a photo to your bot:

1. 🤖 Telegram sends the image to your webhook endpoint
2. 📥 Server downloads the image from Telegram
3. 💾 Original image is saved to Supabase Storage
4. 🔍 YOLO detects license plates
5. 📝 OCR extracts text from plates
6. 🖼️ Annotated image is created and saved to Supabase
7. 💿 All data is saved to your database table

## Prerequisites

1. A Telegram Bot (create one via [@BotFather](https://t.me/BotFather))
2. Your bot token
3. A publicly accessible webhook URL (e.g., Railway, Render deployment)
4. Supabase account with storage bucket configured

## Environment Variables

Add these to your `.env` file or deployment environment:

```bash
# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Webhook URL (your deployed server URL)
WEBHOOK_URL=https://your-domain.railway.app/telegram-webhook

# Supabase Configuration (already set)
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_service_key
BUCKET_NAME=violations

# Model Configuration (already set)
MODEL_URL=your_model_url
```

## Setup Steps

### 1. Get Your Bot Token

1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Copy the bot token (format: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Configure Environment Variables

On Railway/Render:
- Go to your project settings
- Add the environment variables listed above
- Redeploy if needed

### 3. Set Up Webhook

Option A: Using the setup script:
```bash
python setup_telegram_webhook.py setup
```

Option B: Manual setup via API:
```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-domain.railway.app/telegram-webhook"}'
```

### 4. Verify Webhook

Check webhook status:
```bash
python setup_telegram_webhook.py info
```

Or manually:
```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

### 5. Test the Integration

1. Open your bot in Telegram
2. Send `/start` to activate the bot
3. Send a photo containing a license plate
4. Bot will process the image automatically
5. Check your Supabase database for the results

## API Endpoints

### `/telegram-webhook` (POST)
- Receives webhook updates from Telegram
- Automatically processes photos sent to the bot
- Stores images in Supabase
- Detects plates and runs OCR
- Saves results to database

### `/upload` (POST)
- Still accepts direct image uploads
- Supports both file upload and Telegram file_id
- Can be used for programmatic access

Example with Telegram file_id:
```bash
curl -X POST "https://your-domain.railway.app/upload" \
  -H "Content-Type: application/json" \
  -d '{"telegram_file_id": "AgACAgIAAxkBAAI...", "camera_id": "CAM1"}'
```

## Troubleshooting

### Webhook not receiving updates
1. Check webhook URL is HTTPS (required by Telegram)
2. Verify TELEGRAM_BOT_TOKEN is correct
3. Check server logs for errors
4. Ensure your deployment is not sleeping (Railway/Render free tier)

### Images not saving to Supabase
1. Verify SUPABASE_URL and SUPABASE_SERVICE_KEY
2. Check bucket name and permissions
3. Ensure bucket is set to public or has proper access policies
4. Check server logs for upload errors

### OCR not working
1. Verify Tesseract is installed on your deployment
2. Check image quality (plates should be clear and visible)
3. Review preprocessed images in debug folder
4. Adjust detection confidence threshold if needed

### Database not updating
1. Verify table name is "violations"
2. Check table schema matches the insert function
3. Review Supabase logs for insertion errors
4. Ensure service key has insert permissions

## Database Schema

Your `violations` table should have these columns:

```sql
CREATE TABLE violations (
  id BIGSERIAL PRIMARY KEY,
  camera_id TEXT NOT NULL,
  plate_text TEXT,
  confidence FLOAT,
  plate_url TEXT,
  scene_url TEXT,
  timestamp TIMESTAMPTZ DEFAULT NOW(),
  status TEXT DEFAULT 'new',
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Storage Bucket

Your Supabase storage bucket should be configured:

1. Bucket name: `violations` (or update BUCKET_NAME env var)
2. Public access: Enabled (for viewing images)
3. File size limit: Adjust as needed (default 16MB on server)
4. Allowed MIME types: `image/jpeg`, `image/png`, `image/jpg`

## Security Considerations

1. **Bot Token**: Keep your bot token secret. Never commit it to Git.
2. **Service Key**: Use Supabase service role key for server-side operations
3. **Webhook Validation**: Consider adding webhook secret validation
4. **Rate Limiting**: Monitor API usage to prevent abuse
5. **Access Control**: Restrict bot access to authorized users if needed

## Monitoring

Check server logs for:
- Telegram webhook requests
- Image download status
- Supabase upload confirmation
- Detection results
- Database insertion success

Example log output:
```
[TELEGRAM] Webhook received: {...}
[TELEGRAM] Processing photo with file_id: AgACAgIAAxkBAAI...
[INFO] Downloaded 245678 bytes from Telegram
[INFO] Image decoded successfully: (720, 1280, 3)
[INFO] Original image uploaded to Supabase: https://...
[INFO] Found 1 detections
[INFO] Plate detected with confidence: 0.89
[INFO] OCR result: ABC1234
[INFO] Annotated image uploaded to Supabase: https://...
[INFO] Logging 1 plates to database
[SUCCESS] Telegram webhook processed successfully
```

## Additional Commands

Delete webhook (use polling instead):
```bash
python setup_telegram_webhook.py delete
```

Get webhook information:
```bash
python setup_telegram_webhook.py info
```

## Support

For issues or questions:
1. Check server logs for detailed error messages
2. Verify all environment variables are set correctly
3. Test with the `/test` endpoint to ensure server is running
4. Review Telegram Bot API documentation: https://core.telegram.org/bots/api
