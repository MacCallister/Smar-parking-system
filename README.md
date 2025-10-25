# 🚗 Smart Parking System

AI-powered license plate detection and OCR system with Telegram integration and Supabase storage.

## ✨ Features

- 🤖 **Telegram Bot Integration** - Send photos directly to your bot
- 🔍 **YOLO v8 Detection** - Accurate license plate detection
- 📝 **OCR Text Extraction** - Automatic plate number reading
- 💾 **Supabase Storage** - All images saved automatically
- 📊 **Database Logging** - Complete tracking of detections
- 🎨 **Annotated Images** - Visual detection results
- 🌐 **REST API** - Programmatic access available

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/oludaara/Smar-parking-system.git
cd Smar-parking-system
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
Copy `.env.example` to `.env` and fill in your values:
```bash
cp .env.example .env
```

Required environment variables:
- `TELEGRAM_BOT_TOKEN` - From @BotFather
- `WEBHOOK_URL` - Your deployment URL + /telegram-webhook
- `SUPABASE_URL` - From Supabase project settings
- `SUPABASE_SERVICE_KEY` - Service role key
- `BUCKET_NAME` - Storage bucket name
- `MODEL_URL` - YOLO model download URL

### 4. Setup Telegram Webhook
```bash
python setup_telegram_webhook.py setup
```

### 5. Run Server
```bash
python server.py
```

Or deploy to Railway/Render (recommended for webhooks).

## 📚 Documentation

- **[🎯 Quick Reference](QUICK_REFERENCE.md)** - Commands and examples
- **[📱 Telegram Setup](TELEGRAM_SETUP.md)** - Complete integration guide
- **[✅ Deployment Checklist](DEPLOYMENT_CHECKLIST.md)** - Step-by-step deployment
- **[📋 Integration Summary](INTEGRATION_SUMMARY.md)** - Detailed changes and workflow

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/test` | GET | Test endpoint |
| `/upload` | POST | Upload image (file or telegram_file_id) |
| `/telegram-webhook` | POST | Telegram bot webhook |

## 📸 Usage

### Via Telegram Bot
1. Get bot token from [@BotFather](https://t.me/BotFather)
2. Configure webhook with `setup_telegram_webhook.py`
3. Send photos to your bot
4. Images automatically processed and saved

### Via API
```bash
# With Telegram file_id
curl -X POST "https://your-domain/upload" \
  -H "Content-Type: application/json" \
  -d '{"telegram_file_id": "AgACAgIAAxkBAAI...", "camera_id": "CAM1"}'

# With direct file upload
curl -X POST "https://your-domain/upload" \
  -F "camera_id=CAM1" \
  -F "image=@photo.jpg"
```

## 🗄️ Storage Structure

```
supabase/violations/
├── CAM1/
│   ├── 20250124_143022.jpg           # Original image
│   ├── 20250124_143022_plate_0.jpg   # Cropped plate
│   └── 20250124_143022_annotated.jpg # Annotated image
└── TELEGRAM_123456789/
    └── (same structure)
```

## 💿 Database Schema

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

## 🧪 Testing

Run integration tests:
```bash
python test_telegram_integration.py
```

Test webhook configuration:
```bash
python setup_telegram_webhook.py info
```

## 🛠️ Tech Stack

- **Backend**: Flask, Python 3.8+
- **AI/ML**: YOLOv8 (Ultralytics), PyTorch
- **OCR**: Tesseract, pytesseract
- **Storage**: Supabase Storage
- **Database**: Supabase (PostgreSQL)
- **Deployment**: Railway, Render
- **Integration**: Telegram Bot API

## 📦 Dependencies

See [requirements.txt](requirements.txt) for complete list:
- Flask - Web framework
- ultralytics - YOLOv8 implementation
- pytesseract - OCR engine
- opencv-python-headless - Image processing
- supabase - Database and storage client
- gunicorn - Production server

## 🔧 Configuration

### Tesseract OCR
Install Tesseract:
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract

# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
```

### YOLO Model
Model is automatically downloaded from `MODEL_URL` on first run.

## 🚢 Deployment

### Railway
1. Connect GitHub repository
2. Add environment variables
3. Deploy automatically on push

### Render
1. Connect GitHub repository
2. Add environment variables
3. Deploy automatically on push

**Important**: Webhook requires HTTPS (both platforms provide this).

## 🔍 Monitoring

Check server logs for:
- `[TELEGRAM] Webhook received` - Telegram messages
- `[INFO] Downloaded X bytes from Telegram` - Image fetching
- `[INFO] Public URL: https://...` - Supabase uploads
- `[INFO] Logging N plates to database` - Database inserts
- `[SUCCESS] Telegram webhook processed successfully` - Complete workflow

## 🐛 Troubleshooting

### Images not in Supabase
- Verify `SUPABASE_SERVICE_KEY` (use service role, not anon key)
- Check bucket exists and has proper permissions
- Review upload logs in server output

### Webhook not working
- Ensure URL is HTTPS
- Run `python setup_telegram_webhook.py info`
- Check server is publicly accessible

### OCR not reading plates
- Verify image quality
- Check Tesseract installation
- Review preprocessed images in `debug_preprocessed/` folder

See [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md) for detailed troubleshooting.

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 👨‍💻 Author

**Theophilus Bitrus** (oludaara)

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

## ⭐ Show Your Support

Give a ⭐️ if this project helped you!

---

**Need Help?** Check the documentation files or open an issue.