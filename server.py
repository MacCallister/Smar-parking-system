# ======================================================
# Smart Parking Detection Server - PRODUCTION READY
# Flask + YOLOv8 + Tesseract OCR + Supabase + Telegram
# Author: Theophilus Bitrus
# Optimized for Railway deployment
# ======================================================

import os
import cv2
import numpy as np
import pytesseract
import requests
import torch
from ultralytics import YOLO
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, request, jsonify
from supabase import create_client, Client
import mimetypes
import traceback

# ======================================================
# INITIAL SETUP
# ======================================================

torch.set_grad_enabled(False)  # Save memory (no gradients)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# ======================================================
# ENVIRONMENT SETTINGS
# ======================================================
UPLOAD_DIR = "uploads"
OUTPUT_DIR = "cropped_plates"
DEBUG_DIR = "debug_preprocessed"
ANNOTATED_DIR = "annotated"

for d in [UPLOAD_DIR, OUTPUT_DIR, DEBUG_DIR, ANNOTATED_DIR]:
    os.makedirs(d, exist_ok=True)

# Tesseract Path
TESSERACT_CMD = os.getenv("TESSERACT_CMD") or "/usr/bin/tesseract"
if os.path.exists(TESSERACT_CMD):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# ⚠️ UPDATE THIS: Add your Telegram Bot Token to Railway environment variables
# Railway Dashboard → Your Project → Variables → Add Variable
# Name: TELEGRAM_BOT_TOKEN
# Value: 8260428040:AAHopZu53sdpM5-gPxa9nL2-Y2d7tsnOcRI
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    print("[WARNING] TELEGRAM_BOT_TOKEN not set - Telegram webhook will not work")

# ⚠️ UPDATE THIS: Add Supabase credentials to Railway environment variables
# Railway Dashboard → Your Project → Variables → Add these:
# Name: SUPABASE_URL, Value: https://your-project.supabase.co
# Name: SUPABASE_SERVICE_KEY, Value: your-service-role-key (from Supabase settings)
# Name: BUCKET_NAME, Value: violations (or your bucket name)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
BUCKET_NAME = os.getenv("BUCKET_NAME", "violations")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise RuntimeError("Missing Supabase credentials in environment variables")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ======================================================
# YOLO MODEL SETUP
# ======================================================

def download_model():
    """Downloads YOLO model if not already present"""
    # ⚠️ UPDATE THIS: Add MODEL_URL to Railway environment variables
    # Name: MODEL_URL
    # Value: Direct download link to your best.pt model (e.g., Google Drive, Dropbox)
    model_url = os.getenv("MODEL_URL")
    if not model_url:
        raise ValueError("MODEL_URL not found in environment variables")

    os.makedirs("models", exist_ok=True)
    local_path = "models/best.pt"
    if not os.path.exists(local_path):
        print(f"[INFO] Downloading YOLO model from {model_url} ...")
        r = requests.get(model_url, timeout=300)
        r.raise_for_status()
        with open(local_path, "wb") as f:
            f.write(r.content)
        print("[INFO] Model downloaded successfully.")
    return local_path

model_path = download_model()
model = YOLO(model_path)
model.fuse()

# ======================================================
# HELPER FUNCTIONS
# ======================================================

def download_image_from_telegram(file_id):
    """Downloads image from Telegram servers using file_id"""
    try:
        if not TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN not configured")
        
        # Get file path from Telegram API
        get_file_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
        print(f"[INFO] Fetching file info from Telegram: {file_id}")
        
        response = requests.get(get_file_url, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        if not result.get("ok"):
            raise ValueError(f"Telegram API error: {result.get('description', 'Unknown error')}")
        
        file_path = result["result"]["file_path"]
        print(f"[INFO] Telegram file_path: {file_path}")
        
        # Download the actual file
        download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
        print(f"[INFO] Downloading image from Telegram...")
        
        img_response = requests.get(download_url, timeout=30)
        img_response.raise_for_status()
        
        img_bytes = img_response.content
        print(f"[INFO] Downloaded {len(img_bytes)} bytes from Telegram")
        
        return img_bytes
        
    except Exception as e:
        print(f"[ERROR] Failed to download from Telegram: {e}")
        raise


def run_ocr_on_crop(crop, save_name=None):
    """Runs Tesseract OCR on cropped plate image"""
    try:
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        gray = cv2.medianBlur(gray, 3)
        if save_name:
            cv2.imwrite(os.path.join(DEBUG_DIR, save_name), gray)

        text = pytesseract.image_to_string(
            gray,
            config="--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        )
        plate_text = ''.join(c for c in text if c.isalnum())
        return plate_text if plate_text else None

    except Exception as e:
        print(f"[ERROR] OCR failed: {e}")
        return None


def upload_to_supabase_storage(local_path, public_folder=""):
    """Uploads file to Supabase Storage and returns its public URL"""
    try:
        with open(local_path, "rb") as f:
            data = f.read()
        
        folder = str(public_folder or "").strip("/ ")
        file_key = f"{folder}/{Path(local_path).name}" if folder else Path(local_path).name
        
        content_type, _ = mimetypes.guess_type(str(local_path))
        if not content_type:
            content_type = "image/jpeg"
        
        print(f"[INFO] Uploading to Supabase: bucket='{BUCKET_NAME}' key='{file_key}' size={len(data)} bytes")

        supabase.storage.from_(BUCKET_NAME).upload(
            file_key, data, {"content-type": content_type, "upsert": "true"}
        )

        public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(file_key)
        print(f"[INFO] Public URL: {public_url}")
        
        return public_url
        
    except Exception as e:
        print(f"[ERROR] Supabase upload failed: {e}")
        traceback.print_exc()
        return None


def insert_plate_record(camera_id, plate_text, confidence, plate_url, scene_url):
    """Inserts detection record into Supabase table"""
    try:
        row = {
            "camera_id": camera_id,
            "plate_text": plate_text,
            "confidence": float(confidence),
            "plate_url": plate_url,
            "scene_url": scene_url,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "new",
        }
        supabase.table("violations").insert(row).execute()
        print(f"[INFO] Inserted record to database: camera={camera_id}, plate={plate_text}")
        return True
    except Exception as e:
        print(f"[ERROR] Supabase insert error: {e}")
        traceback.print_exc()
        return False


def process_image(img_bytes, camera_id):
    """Process image with YOLO detection and OCR"""
    try:
        # Decode image
        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        if img is None:
            return {"error": "Failed to decode image"}

        print(f"[INFO] Image decoded successfully: {img.shape}")

        # Save raw image
        filename = datetime.now().strftime("%Y%m%d_%H%M%S.jpg")
        save_path = os.path.join(UPLOAD_DIR, filename)
        cv2.imwrite(save_path, img)
        print(f"[INFO] Image saved to {save_path}")

        # Run YOLO detection
        print("[INFO] Running YOLO detection...")
        results = model.predict(img, conf=0.5, imgsz=320, device="cpu", verbose=False)
        annotated = img.copy()
        detected_plates = []

        # Process results
        for r in results:
            if not hasattr(r, "boxes") or r.boxes is None or len(r.boxes) == 0:
                continue

            boxes = r.boxes.xyxy.cpu().numpy()
            class_ids = r.boxes.cls.cpu().numpy().astype(int)
            confs = r.boxes.conf.cpu().numpy()

            print(f"[INFO] Found {len(boxes)} detections")

            for i, box in enumerate(boxes):
                x1, y1, x2, y2 = map(int, box[:4])
                confidence = float(confs[i])
                
                if x2 <= x1 or y2 <= y1:
                    continue

                class_name = model.names[class_ids[i]] if hasattr(model, "names") else str(class_ids[i])
                if class_name.lower() != "plate":
                    continue

                print(f"[INFO] Plate detected with confidence: {confidence:.2f}")

                # Draw detection box
                cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(annotated, f"{class_name} {confidence:.2f}", (x1, y1 - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                # Crop and OCR
                crop = img[y1:y2, x1:x2]
                crop_name = f"{os.path.splitext(filename)[0]}_plate_{i}.jpg"
                crop_path = os.path.join(OUTPUT_DIR, crop_name)
                cv2.imwrite(crop_path, crop)

                plate_text = run_ocr_on_crop(crop, crop_name)
                print(f"[INFO] OCR result: {plate_text or 'unreadable'}")
                
                plate_url = upload_to_supabase_storage(crop_path, camera_id)

                detected_plates.append({
                    "file": crop_name,
                    "text": plate_text or "unreadable",
                    "plate_url": plate_url,
                    "confidence": confidence
                })

        # Save annotated image
        ann_name = f"{os.path.splitext(filename)[0]}_annotated.jpg"
        ann_path = os.path.join(ANNOTATED_DIR, ann_name)
        cv2.imwrite(ann_path, annotated)
        scene_url = upload_to_supabase_storage(ann_path, camera_id)

        # Log to database
        if not detected_plates:
            print("[INFO] No plates detected in image")
            insert_plate_record(camera_id, "no_plate_detected", 0.0, None, scene_url)
            result = {
                "status": "no_plate_detected",
                "file": filename,
                "scene_url": scene_url,
                "message": "Image processed but no license plates found"
            }
        else:
            print(f"[INFO] Logging {len(detected_plates)} plates to database")
            for dp in detected_plates:
                insert_plate_record(camera_id, dp["text"], dp["confidence"], dp.get("plate_url"), scene_url)
            
            result = {
                "status": "ok",
                "file": filename,
                "scene_url": scene_url,
                "plates": detected_plates,
                "message": f"Successfully detected {len(detected_plates)} plate(s)"
            }

        # Clean up
        del img, annotated
        cv2.destroyAllWindows()

        print("[SUCCESS] Image processing completed\n")
        return result

    except Exception as e:
        print(f"[ERROR] Image processing failed: {e}")
        traceback.print_exc()
        return {"error": str(e)}

# ======================================================
# API ROUTES
# ======================================================

@app.route("/")
def index():
    return jsonify({
        "status": "ok",
        "service": "Smart Parking Detection Server",
        "version": "2.0",
        "endpoints": {
            "/": "Service info (GET)",
            "/test": "Health check (GET)",
            "/upload": "Upload image for processing (POST)",
            "/telegram-webhook": "Telegram bot webhook (POST)",
            "/setup-webhook": "Setup Telegram webhook (GET)"
        },
        "telegram_configured": TELEGRAM_BOT_TOKEN is not None
    })


@app.route("/test")
def test():
    return jsonify({
        "status": "ok", 
        "message": "Server is healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


@app.route("/upload", methods=["GET", "POST"])
def upload_image():
    """Main route: receives image or Telegram file_id, runs detection + OCR"""
    
    # Handle GET requests - return endpoint info
    if request.method == "GET":
        return jsonify({
            "endpoint": "/upload",
            "method": "POST",
            "status": "ready",
            "message": "This endpoint accepts POST requests with image data or Telegram file_id",
            "accepted_formats": {
                "multipart_form": "Form field 'image' or 'file' with image file",
                "telegram": "Form field 'telegram_file_id' with Telegram file ID",
                "raw": "Raw image bytes in request body"
            },
            "optional_parameters": {
                "camera_id": "Camera identifier (defaults to CAM1)"
            },
            "examples": [
                "curl -X POST https://your-domain/upload -F 'image=@photo.jpg' -F 'camera_id=CAM001'",
                "curl -X POST https://your-domain/upload -F 'telegram_file_id=ABC123' -F 'camera_id=CAM001'"
            ]
        }), 200
    
    # Handle POST requests - process image
    print("\n" + "="*60)
    print(f"[UPLOAD] New request received at {datetime.now()}")
    print(f"Content-Type: {request.content_type}")
    print(f"Content-Length: {request.content_length}")
    print("="*60 + "\n")
    
    try:
        # Get camera ID
        camera_id = request.form.get("camera_id") or request.headers.get("X-Camera-ID", "CAM1")
        print(f"[INFO] Camera ID: {camera_id}")

        # Get image bytes
        img_bytes = None
        telegram_file_id = request.form.get("telegram_file_id")
        
        # Priority 1: Telegram file_id
        if telegram_file_id:
            print(f"[INFO] Telegram file_id provided: {telegram_file_id}")
            img_bytes = download_image_from_telegram(telegram_file_id)
        # Priority 2: Multipart form data with "image" field
        elif "image" in request.files:
            print("[INFO] Image found in request.files['image']")
            img_bytes = request.files["image"].read()
        # Priority 3: "file" field
        elif "file" in request.files:
            print("[INFO] Image found in request.files['file']")
            img_bytes = request.files["file"].read()
        # Priority 4: Raw request data
        elif request.data and len(request.data) > 0:
            print("[INFO] Image found in request.data")
            img_bytes = request.data
        else:
            print("[ERROR] No image data found in request")
            return jsonify({
                "error": "No image data or telegram_file_id received",
                "hint": "Send image as multipart form-data with field name 'image' or provide 'telegram_file_id'"
            }), 400

        if not img_bytes or len(img_bytes) == 0:
            return jsonify({"error": "Empty image data received"}), 400

        print(f"[INFO] Received {len(img_bytes)} bytes of image data")

        # Process the image
        result = process_image(img_bytes, camera_id)
        
        if "error" in result:
            return jsonify(result), 400
        
        return jsonify(result), 200

    except Exception as e:
        error_details = traceback.format_exc()
        print(f"[ERROR] Upload failed: {e}")
        print(f"[ERROR] Traceback:\n{error_details}")
        
        return jsonify({
            "error": str(e),
            "type": type(e).__name__
        }), 500


@app.route("/telegram-webhook", methods=["POST", "GET"])
def telegram_webhook():
    """
    Telegram webhook endpoint - automatically processes images sent to bot
    
    ⚠️ SETUP REQUIRED: After deploying, visit /setup-webhook to configure
    """
    # Handle GET requests (for Telegram verification)
    if request.method == "GET":
        return jsonify({
            "status": "ok",
            "message": "Telegram webhook endpoint is active",
            "note": "This endpoint receives POST requests from Telegram"
        }), 200
    
    try:
        data = request.get_json()
        print(f"[TELEGRAM] Webhook received: {data}")
        
        # Extract message data
        message = data.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        
        # Check for photo
        photo = message.get("photo")
        if not photo:
            print("[TELEGRAM] No photo in message")
            return jsonify({"ok": True}), 200
        
        # Get the largest photo (last in array)
        largest_photo = photo[-1]
        file_id = largest_photo.get("file_id")
        
        if not file_id:
            print("[TELEGRAM] No file_id in photo")
            return jsonify({"ok": True}), 200
        
        print(f"[TELEGRAM] Processing photo with file_id: {file_id}")
        
        # Extract camera_id from caption if provided
        caption = message.get("caption", "")
        camera_id = f"TELEGRAM_{chat_id}"
        
        if caption:
            caption_upper = caption.upper()
            if "CAM" in caption_upper:
                words = caption_upper.split()
                for word in words:
                    if word.startswith("CAM"):
                        camera_id = word
                        break
        
        print(f"[INFO] Using camera_id: {camera_id}")
        
        # Download and process image
        img_bytes = download_image_from_telegram(file_id)
        result = process_image(img_bytes, camera_id)
        
        # Send response back to Telegram
        if "error" in result:
            response_text = f"❌ Error: {result['error']}"
        elif result.get("status") == "no_plate_detected":
            response_text = f"⚠️ No license plate detected\n📷 Camera: {camera_id}\n✅ Image saved to database for review"
        else:
            plates_list = result.get("plates", [])
            plates_text = "\n".join([f"• {p['text']} ({p['confidence']*100:.1f}%)" for p in plates_list])
            response_text = f"✅ Detected {len(plates_list)} plate(s)!\n📷 Camera: {camera_id}\n\n{plates_text}\n\n✅ Saved to database"
        
        # Send response to user
        send_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(send_url, json={
            "chat_id": chat_id,
            "text": response_text
        }, timeout=5)
        
        print("[SUCCESS] Telegram webhook processed\n")
        return jsonify({"ok": True}), 200
        
    except Exception as e:
        print(f"[ERROR] Telegram webhook failed: {e}")
        traceback.print_exc()
        # Always return 200 to Telegram to avoid retries
        return jsonify({"ok": True}), 200


@app.route("/check-webhook", methods=["GET"])
def check_webhook():
    """Check current Telegram webhook status"""
    try:
        if not TELEGRAM_BOT_TOKEN:
            return jsonify({"error": "TELEGRAM_BOT_TOKEN not configured"}), 500
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return jsonify({
                "status": "success",
                "webhook_info": data.get("result", {}),
                "current_url": data.get("result", {}).get("url", "Not set")
            })
        else:
            return jsonify({"error": response.text}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/setup-webhook", methods=["GET"])
def setup_telegram_webhook():
    """
    Setup Telegram webhook - Visit this URL once after deployment
    
    ⚠️ IMPORTANT: After deploying to Railway, visit:
    https://your-railway-domain/setup-webhook
    
    This configures Telegram to send photos to your server automatically
    """
    try:
        if not TELEGRAM_BOT_TOKEN:
            return jsonify({
                "error": "TELEGRAM_BOT_TOKEN not configured",
                "instruction": "Add TELEGRAM_BOT_TOKEN to Railway environment variables"
            }), 500
        
        # Get your Railway URL
        webhook_url = request.host_url.rstrip('/') + '/telegram-webhook'
        
        print(f"[INFO] Setting up Telegram webhook: {webhook_url}")
        
        # Set webhook
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"
        response = requests.post(url, json={"url": webhook_url}, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"[SUCCESS] Webhook configured: {data}")
            return jsonify({
                "status": "success",
                "message": "✅ Telegram webhook configured successfully!",
                "webhook_url": webhook_url,
                "telegram_response": data,
                "next_steps": [
                    "1. Send a photo to your Telegram bot",
                    "2. Check your dashboard for new violations",
                    "3. The bot will reply with detection results"
                ]
            })
        else:
            return jsonify({
                "error": "Failed to set webhook",
                "status_code": response.status_code,
                "response": response.text
            }), 500
            
    except Exception as e:
        print(f"[ERROR] Webhook setup failed: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ======================================================
# ERROR HANDLERS
# ======================================================

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "File too large. Maximum size is 16MB"}), 413


@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Endpoint not found",
        "available_endpoints": {
            "/": "Service info",
            "/test": "Health check",
            "/upload": "Upload image",
            "/telegram-webhook": "Telegram webhook",
            "/setup-webhook": "Setup Telegram webhook"
        }
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


# ======================================================
# MAIN ENTRY POINT
# ======================================================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug_mode = os.getenv("DEBUG", "False").lower() == "true"
    
    print(f"\n{'='*60}")
    print(f"🚀 Smart Parking Detection Server Starting")
    print(f"{'='*60}")
    print(f"Port: {port}")
    print(f"Debug: {debug_mode}")
    print(f"Telegram: {'✅ Configured' if TELEGRAM_BOT_TOKEN else '❌ Not configured'}")
    print(f"Supabase: {'✅ Configured' if SUPABASE_URL else '❌ Not configured'}")
    print(f"{'='*60}\n")
    
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
