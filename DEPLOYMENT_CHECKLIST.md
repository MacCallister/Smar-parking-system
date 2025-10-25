# 🚀 Deployment Checklist

Use this checklist to ensure your Telegram integration is properly deployed and working.

## Pre-Deployment

- [ ] Review changes in `server.py`
- [ ] Read `TELEGRAM_SETUP.md` for detailed instructions
- [ ] Have your Telegram Bot Token ready (from @BotFather)
- [ ] Know your deployment URL (Railway/Render)

## Deployment Steps

### 1. Environment Variables

Set these in your Railway/Render dashboard:

- [ ] `TELEGRAM_BOT_TOKEN` = `your_bot_token_from_botfather`
- [ ] `WEBHOOK_URL` = `https://your-domain.railway.app/telegram-webhook`
- [ ] `SUPABASE_URL` = `your_existing_supabase_url`
- [ ] `SUPABASE_SERVICE_KEY` = `your_service_role_key`
- [ ] `BUCKET_NAME` = `violations` (or your bucket name)
- [ ] `MODEL_URL` = `your_model_download_url`

### 2. Deploy Code

**If using Git:**
```bash
git add .
git commit -m "Add Telegram integration for image fetching and Supabase storage"
git push
```

**Railway:** Automatically deploys on push  
**Render:** Automatically deploys on push

### 3. Verify Deployment

- [ ] Check deployment logs for errors
- [ ] Visit `https://your-domain.railway.app/` - should return health check
- [ ] Visit `https://your-domain.railway.app/test` - should return test success

### 4. Configure Telegram Webhook

**Option A: Use the setup script (locally)**
```bash
# Make sure .env has TELEGRAM_BOT_TOKEN and WEBHOOK_URL
python setup_telegram_webhook.py setup
```

**Option B: Manual API call**
```bash
curl -X POST "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-domain.railway.app/telegram-webhook"}'
```

- [ ] Webhook setup returns success
- [ ] Run `python setup_telegram_webhook.py info` to verify

### 5. Test Integration

- [ ] Open your bot in Telegram
- [ ] Send `/start` command
- [ ] Send a photo with a license plate
- [ ] Check server logs for processing messages
- [ ] Verify image appears in Supabase Storage
- [ ] Verify record appears in violations table

### 6. Verify Supabase Storage

Go to your Supabase dashboard > Storage > violations bucket:

- [ ] Original image exists (e.g., `TELEGRAM_123456/20250124_143530_telegram.jpg`)
- [ ] Cropped plate exists (e.g., `TELEGRAM_123456/20250124_143530_telegram_plate_0.jpg`)
- [ ] Annotated image exists (e.g., `TELEGRAM_123456/20250124_143530_telegram_annotated.jpg`)
- [ ] Images are publicly accessible (or have proper access)

### 7. Verify Database

Query your violations table:

```sql
SELECT * FROM violations ORDER BY timestamp DESC LIMIT 10;
```

Check that recent records have:
- [ ] `camera_id` populated (e.g., "TELEGRAM_123456789")
- [ ] `plate_text` extracted (or "unreadable"/"no_plate_detected")
- [ ] `confidence` value set
- [ ] `plate_url` is a valid Supabase URL (not null for detected plates)
- [ ] `scene_url` is a valid Supabase URL
- [ ] `timestamp` is correct
- [ ] `status` is "new"

## Testing Checklist

Run these tests after deployment:

### Test 1: Server Health
```bash
curl https://your-domain.railway.app/
```
**Expected:** `{"status": "ok", "message": "..."}`

### Test 2: Upload Endpoint Info
```bash
curl https://your-domain.railway.app/upload
```
**Expected:** JSON with endpoint information

### Test 3: Telegram Bot
1. Send photo to bot
2. Check logs: `[TELEGRAM] Webhook received`
3. Check logs: `[INFO] Downloaded X bytes from Telegram`
4. Check logs: `[INFO] Public URL: https://...`
5. Check logs: `[SUCCESS] Telegram webhook processed successfully`

### Test 4: Webhook Status
```bash
python setup_telegram_webhook.py info
```
**Expected:** 
- URL is set to your webhook endpoint
- No errors reported
- Pending updates: 0 (after test)

### Test 5: Manual Upload with file_id
```bash
# Get a file_id by checking your server logs or Telegram updates
curl -X POST "https://your-domain.railway.app/upload" \
  -H "Content-Type: application/json" \
  -d '{"telegram_file_id": "AgACAgIAAxkBAAI...", "camera_id": "TEST"}'
```
**Expected:** 200 status with detection results

## Troubleshooting

### Issue: Webhook not receiving updates

**Check:**
- [ ] Webhook URL is HTTPS
- [ ] Server is accessible from internet
- [ ] TELEGRAM_BOT_TOKEN is correct
- [ ] Run `python setup_telegram_webhook.py info` for errors

**Fix:**
```bash
python setup_telegram_webhook.py delete
python setup_telegram_webhook.py setup
```

### Issue: Images not in Supabase

**Check server logs for:**
```
[INFO] Uploading to Supabase bucket='violations' key='...'
[INFO] Public URL: https://...
```

**If missing, verify:**
- [ ] SUPABASE_SERVICE_KEY is service role key (not anon)
- [ ] Bucket name is correct
- [ ] Bucket exists and is accessible
- [ ] Check Supabase logs for errors

**Test upload manually:**
```python
from supabase import create_client
import os

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

# Try uploading a test file
with open("test.jpg", "rb") as f:
    res = supabase.storage.from_("violations").upload("test/test.jpg", f.read())
print(res)
```

### Issue: Database not updating

**Check:**
- [ ] Table name is "violations"
- [ ] Service key has INSERT permission
- [ ] Table schema matches expected columns

**Verify schema:**
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

### Issue: OCR not working

**Check:**
- [ ] Tesseract is installed on server
- [ ] Image quality is good
- [ ] Detection confidence is reasonable

**Test locally:**
```bash
python -c "import pytesseract; print(pytesseract.get_tesseract_version())"
```

## Success Criteria

✅ **All checked** = Ready to use!

- [ ] Server deployed and running
- [ ] Webhook configured and verified
- [ ] Test image processed successfully
- [ ] Original image in Supabase Storage
- [ ] Annotated image in Supabase Storage
- [ ] Cropped plate in Supabase Storage (if plate detected)
- [ ] Record in database with URLs
- [ ] Server logs show success messages
- [ ] No errors in Telegram webhook info

## Post-Deployment

- [ ] Monitor server logs for any errors
- [ ] Test with multiple images
- [ ] Verify storage costs (if applicable)
- [ ] Set up monitoring/alerts (optional)
- [ ] Document any custom configurations

## Maintenance

### Regular Checks
- Monitor storage usage in Supabase
- Review database records for accuracy
- Check webhook status periodically
- Review server logs for errors

### If Webhook Stops Working
```bash
# Re-register webhook
python setup_telegram_webhook.py setup

# Check for errors
python setup_telegram_webhook.py info
```

### Updating the Bot
1. Update code
2. Deploy
3. Webhook continues working (no re-setup needed unless URL changes)

## Notes

- Telegram webhooks require HTTPS
- Server must return 200 within 60 seconds
- Images larger than 20MB may fail
- Free tier limitations may apply (Railway/Render)

---

**Need Help?**
- Review server logs first
- Check `TELEGRAM_SETUP.md` for detailed troubleshooting
- Run `python test_telegram_integration.py` for diagnostics
- Verify all environment variables are set correctly
