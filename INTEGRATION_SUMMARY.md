# 🚀 Smart Parking System - Telegram Integration Update

## What Was Changed

Your server has been updated to fetch images from Telegram, save them to Supabase, detect plates, extract text, and save everything to your database.

## Key Changes Made

### 1. **server.py** - Main Server Updates

#### New Environment Variable
- Added `TELEGRAM_BOT_TOKEN` configuration for Telegram API access

#### New Function: `download_image_from_telegram(file_id)`
- Downloads images directly from Telegram servers using file_id
- Handles Telegram API authentication
- Returns image bytes for processing

#### Updated `/upload` Endpoint
- Now accepts **both** direct file uploads and Telegram file_id
- Priority order:
  1. `telegram_file_id` (JSON or form data)
  2. Multipart file upload (`image` field)
  3. Alternative file field (`file`)
  4. Raw request data

#### New `/telegram-webhook` Endpoint
- Dedicated webhook for Telegram Bot integration
- Automatically processes photos sent to your bot
- Complete workflow:
  1. Receives webhook from Telegram
  2. Downloads image from Telegram
  3. **Saves original image to Supabase Storage**
  4. Runs YOLO detection
  5. Performs OCR on detected plates
  6. **Saves cropped plates to Supabase Storage**
  7. Creates annotated image
  8. **Saves annotated image to Supabase Storage**
  9. **Inserts all data into database table**
- Returns 200 status to prevent Telegram retries

### 2. **setup_telegram_webhook.py** - Webhook Configuration Tool

A utility script to manage your Telegram webhook:
- `python setup_telegram_webhook.py setup` - Configure webhook
- `python setup_telegram_webhook.py info` - Check webhook status
- `python setup_telegram_webhook.py delete` - Remove webhook

### 3. **test_telegram_integration.py** - Testing Tool

Comprehensive test script to verify:
- Environment variables are set correctly
- Telegram image download works
- Upload endpoint functions properly
- Webhook is configured correctly

### 4. **Documentation Files**

- **TELEGRAM_SETUP.md** - Complete setup guide with troubleshooting
- **.env.example** - Environment variable template
- **INTEGRATION_SUMMARY.md** - This file

## How It Works Now

### Flow 1: Telegram Bot (Recommended)

```
User sends photo to Telegram Bot
         ↓
Telegram sends webhook to /telegram-webhook
         ↓
Server downloads image from Telegram
         ↓
Image saved to Supabase Storage (original)
         ↓
YOLO detects license plates
         ↓
OCR extracts plate text
         ↓
Cropped plates saved to Supabase Storage
         ↓
Annotated image saved to Supabase Storage
         ↓
Data inserted into violations table
         ↓
Success response sent to Telegram
```

### Flow 2: Direct Upload (Still Supported)

```
POST to /upload with image file or telegram_file_id
         ↓
Server processes image
         ↓
(Same detection and storage workflow)
         ↓
JSON response with results
```

## Setup Instructions

### Step 1: Get Telegram Bot Token

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow instructions to create bot
4. Copy the bot token (looks like: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Step 2: Configure Environment Variables

Add to your Railway/Render environment:

```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
WEBHOOK_URL=https://your-domain.railway.app/telegram-webhook
```

### Step 3: Setup Webhook

Run the setup script:
```bash
python setup_telegram_webhook.py setup
```

Or manually via API:
```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-domain.railway.app/telegram-webhook"}'
```

### Step 4: Test

1. Send a photo to your bot
2. Check server logs for processing
3. Verify image appears in Supabase Storage
4. Check database for new record

Run test script for verification:
```bash
python test_telegram_integration.py
```

## Supabase Storage Structure

Images are now organized by camera_id (or Telegram chat_id):

```
violations/
├── CAM1/
│   ├── 20250124_143022.jpg (original scene)
│   ├── 20250124_143022_plate_0.jpg (cropped plate)
│   └── 20250124_143022_annotated.jpg (with detection boxes)
├── TELEGRAM_123456789/
│   ├── 20250124_143530_telegram.jpg
│   ├── 20250124_143530_telegram_plate_0.jpg
│   └── 20250124_143530_telegram_annotated.jpg
```

## Database Records

Each detection creates a record in the `violations` table:

```sql
{
  "camera_id": "TELEGRAM_123456789",
  "plate_text": "ABC1234",
  "confidence": 0.89,
  "plate_url": "https://...supabase.co/storage/v1/object/public/violations/...",
  "scene_url": "https://...supabase.co/storage/v1/object/public/violations/...",
  "timestamp": "2025-01-24T14:35:30.123Z",
  "status": "new"
}
```

## API Endpoints

### GET `/`
Health check endpoint
```json
{"status": "ok", "message": "Smart Parking Detection Server is running"}
```

### GET `/test`
Test endpoint
```json
{"status": "ok", "message": "Test successful"}
```

### POST `/telegram-webhook`
Telegram webhook endpoint (automatically receives bot messages)
- Processes photos automatically
- Returns 200 to Telegram

### POST `/upload`
Upload endpoint with multiple input options:

**Option 1: Telegram file_id (JSON)**
```bash
curl -X POST "https://your-domain/upload" \
  -H "Content-Type: application/json" \
  -d '{"telegram_file_id": "AgACAgIAAxkBAAI...", "camera_id": "CAM1"}'
```

**Option 2: Direct file upload**
```bash
curl -X POST "https://your-domain/upload" \
  -F "camera_id=CAM1" \
  -F "image=@photo.jpg"
```

## Success Indicators

✅ **Server Returns 200**: Request processed successfully  
✅ **Images in Supabase**: Check your violations bucket  
✅ **Database Records**: Query your violations table  
✅ **Server Logs**: Show successful upload confirmations  

## Troubleshooting

### Images Not Showing in Supabase

**Check 1: Bucket Configuration**
- Verify bucket name matches `BUCKET_NAME` env variable
- Ensure bucket is public or has proper policies
- Check file size limits

**Check 2: Upload Function**
Look for these log messages:
```
[INFO] Uploading to Supabase bucket='violations' key='...'
[INFO] Public URL: https://...
```

If upload fails, check:
- SUPABASE_SERVICE_KEY is correct (service role, not anon key)
- Bucket exists and is accessible
- Network connectivity

**Check 3: API Response**
The `upload_to_supabase_storage` function should return a URL, not None:
```python
plate_url = upload_to_supabase_storage(crop_path, camera_id)
# plate_url should be: "https://...supabase.co/storage/v1/object/public/..."
```

### Telegram Images Not Processing

**Check 1: Bot Token**
```bash
curl "https://api.telegram.org/bot<TOKEN>/getMe"
# Should return bot info
```

**Check 2: Webhook Setup**
```bash
python setup_telegram_webhook.py info
# Should show webhook URL
```

**Check 3: Server Accessibility**
- Webhook URL must be HTTPS
- Server must be publicly accessible
- Check Railway/Render deployment status

### Database Not Updating

**Check 1: Table Schema**
```sql
-- Run in Supabase SQL editor
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'violations';
```

**Check 2: Permissions**
Ensure service key has INSERT permission on violations table

**Check 3: Server Logs**
Look for:
```
[INFO] Logging 1 plates to database
```

If you see errors, check table name and column names match

## Environment Variables Checklist

- [ ] `TELEGRAM_BOT_TOKEN` - From @BotFather
- [ ] `WEBHOOK_URL` - Your server's /telegram-webhook URL  
- [ ] `SUPABASE_URL` - From Supabase project settings
- [ ] `SUPABASE_SERVICE_KEY` - Service role key (not anon)
- [ ] `BUCKET_NAME` - Storage bucket name (default: violations)
- [ ] `MODEL_URL` - YOLO model download URL
- [ ] `PORT` - Server port (optional, default: 5000)

## Next Steps

1. ✅ Deploy updated server code to Railway/Render
2. ✅ Add environment variables to deployment
3. ✅ Run webhook setup script
4. ✅ Test by sending image to bot
5. ✅ Verify images in Supabase Storage
6. ✅ Verify records in database table

## Testing Commands

```bash
# Test webhook configuration
python setup_telegram_webhook.py info

# Run integration tests
python test_telegram_integration.py

# Check bot info
curl "https://api.telegram.org/bot<TOKEN>/getMe"

# Send test request with file_id
curl -X POST "https://your-domain/upload" \
  -H "Content-Type: application/json" \
  -d '{"telegram_file_id": "YOUR_FILE_ID", "camera_id": "TEST"}'
```

## Support Files Created

1. ✅ `server.py` - Updated main server
2. ✅ `setup_telegram_webhook.py` - Webhook configuration tool
3. ✅ `test_telegram_integration.py` - Testing suite
4. ✅ `TELEGRAM_SETUP.md` - Complete setup guide
5. ✅ `.env.example` - Environment template
6. ✅ `INTEGRATION_SUMMARY.md` - This summary

## Important Notes

- **Images are now saved**: Both original, cropped plates, and annotated versions go to Supabase
- **Telegram is prioritized**: If you send telegram_file_id, it downloads from Telegram
- **Backward compatible**: Direct file uploads still work
- **Webhook returns 200**: Always returns success to Telegram (prevents retry loops)
- **Chat ID becomes camera_id**: Format: `TELEGRAM_<chat_id>`

## What You Need to Do

1. **Deploy the updated code** to your server
2. **Add TELEGRAM_BOT_TOKEN** to environment variables
3. **Add WEBHOOK_URL** to environment variables
4. **Run webhook setup** (`python setup_telegram_webhook.py setup`)
5. **Test by sending a photo** to your bot
6. **Check Supabase Storage** for the images
7. **Check database** for the records

---

**Status**: ✅ Code updated and ready for deployment  
**Testing**: Run `python test_telegram_integration.py` after deployment  
**Documentation**: See `TELEGRAM_SETUP.md` for detailed instructions
