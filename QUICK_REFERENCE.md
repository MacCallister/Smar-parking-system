# 🎯 Quick Reference Card

## Environment Variables (Add to Railway/Render)

```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
WEBHOOK_URL=https://your-domain.railway.app/telegram-webhook
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key
BUCKET_NAME=violations
MODEL_URL=https://your-model-url.com/best.pt
```

## Setup Commands

```bash
# Setup webhook
python setup_telegram_webhook.py setup

# Check webhook status
python setup_telegram_webhook.py info

# Remove webhook
python setup_telegram_webhook.py delete

# Run integration tests
python test_telegram_integration.py
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Health check |
| `/test` | GET | Test endpoint |
| `/upload` | GET | Endpoint info |
| `/upload` | POST | Upload image (file or telegram_file_id) |
| `/telegram-webhook` | POST | Telegram bot webhook (auto) |

## Usage Examples

### Send image via Telegram Bot
1. Send photo to your bot
2. Bot automatically processes it

### Upload with telegram_file_id
```bash
curl -X POST "https://your-domain/upload" \
  -H "Content-Type: application/json" \
  -d '{"telegram_file_id": "AgACAgIAAxkBAAI...", "camera_id": "CAM1"}'
```

### Direct file upload (still works)
```bash
curl -X POST "https://your-domain/upload" \
  -F "camera_id=CAM1" \
  -F "image=@photo.jpg"
```

## What Gets Saved to Supabase

```
violations/
├── CAM1/
│   ├── 20250124_143022.jpg           ← Original image
│   ├── 20250124_143022_plate_0.jpg   ← Cropped plate
│   └── 20250124_143022_annotated.jpg ← With detection boxes
└── TELEGRAM_123456789/
    └── (same structure for Telegram images)
```

## Database Record Example

```json
{
  "camera_id": "TELEGRAM_123456789",
  "plate_text": "ABC1234",
  "confidence": 0.89,
  "plate_url": "https://...supabase.co/.../plate_0.jpg",
  "scene_url": "https://...supabase.co/.../annotated.jpg",
  "timestamp": "2025-01-24T14:35:30Z",
  "status": "new"
}
```

## Success Indicators

✅ Server returns 200  
✅ Logs show: `[INFO] Public URL: https://...`  
✅ Images visible in Supabase Storage  
✅ Records in violations table  
✅ Webhook info shows no errors  

## Common Issues & Quick Fixes

### Images not in Supabase
```bash
# Check service key (not anon key)
# Verify bucket name
# Check bucket is public or has access policy
```

### Webhook not working
```bash
python setup_telegram_webhook.py setup
python setup_telegram_webhook.py info
```

### Server not receiving images
```bash
# Check server is running
curl https://your-domain.railway.app/
# Should return: {"status": "ok", ...}
```

## Testing Flow

1. Deploy code ✓
2. Set environment variables ✓
3. Setup webhook: `python setup_telegram_webhook.py setup` ✓
4. Send photo to bot ✓
5. Check Supabase Storage ✓
6. Check database table ✓

## Important Notes

- Telegram file_id has priority over direct uploads
- Webhook must be HTTPS
- Server must return 200 within 60 seconds
- All images (original, cropped, annotated) are saved
- Camera ID format: `TELEGRAM_<chat_id>` for bot messages

## Files Created

- `server.py` - Updated server with Telegram support
- `setup_telegram_webhook.py` - Webhook configuration tool
- `test_telegram_integration.py` - Testing suite
- `TELEGRAM_SETUP.md` - Full setup guide
- `INTEGRATION_SUMMARY.md` - Detailed summary
- `DEPLOYMENT_CHECKLIST.md` - Step-by-step deployment
- `.env.example` - Environment template
- `QUICK_REFERENCE.md` - This file

## Support Resources

- **Detailed Setup**: See `TELEGRAM_SETUP.md`
- **Deployment Steps**: See `DEPLOYMENT_CHECKLIST.md`
- **Summary**: See `INTEGRATION_SUMMARY.md`
- **Testing**: Run `python test_telegram_integration.py`

---
**Status**: Ready to deploy! 🚀
