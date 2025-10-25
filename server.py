# ======================================================
# Smart Parking Detection Server
# Flask + YOLOv8 + Tesseract OCR + Supabase Integration
# Author: Theophilus Bitrus
# Optimized for Railway/Render free-tier deployment
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

# Tesseract Path (if custom)
TESSERACT_CMD = os.getenv("TESSERACT_CMD") or "/usr/bin/tesseract"
if os.path.exists(TESSERACT_CMD):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    print("[WARNING] TELEGRAM_BOT_TOKEN not set - Telegram image fetching will not work")

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
BUCKET_NAME = os.getenv("BUCKET_NAME", "violations")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise RuntimeError("Missing Supabase credentials in environment")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ======================================================
# YOLO MODEL SETUP
# ======================================================

def download_model():
    """Downloads YOLO model if not already present"""
    model_url = os.getenv("MODEL_URL")
    if not model_url:
        raise ValueError("MODEL_URL not found in environment variables")

    os.makedirs("models", exist_ok=True)
    local_path = "models/best.pt"
    if not os.path.exists(local_path):
        print(f"[INFO] Downloading YOLO model from {model_url} ...")
        r = requests.get(model_url)
        r.raise_for_status()
        with open(local_path, "wb") as f:
            f.write(r.content)
        print("[INFO] Model downloaded successfully.")
    return local_path

model_path = download_model()
model = YOLO(model_path)
model.fuse()  # Optimizes layers for faster inference

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
        # Ensure no leading/trailing slashes produce malformed keys
        folder = str(public_folder or "").strip("/ ")
        file_key = f"{folder}/{Path(local_path).name}" if folder else f"{Path(local_path).name}"
        content_type, _ = mimetypes.guess_type(str(local_path))
        if not content_type:
            content_type = "image/jpeg"
        print(f"[INFO] Uploading to Supabase bucket='{BUCKET_NAME}' key='{file_key}' content_type='{content_type}' size={len(data)}")

        res = supabase.storage.from_(BUCKET_NAME).upload(
            file_key, data, {"content-type": content_type}, upsert=True
        )

        # Some supabase client versions return a Response-like object; print for debugging
        try:
            print(f"[DEBUG] Supabase upload response: {res}")
        except Exception:
            pass

        # get_public_url may return dict or string depending on client; normalize it
        public = supabase.storage.from_(BUCKET_NAME).get_public_url(file_key)
        if isinstance(public, dict) and public.get("publicUrl"):
            public_url = public.get("publicUrl")
        elif isinstance(public, dict) and public.get("public_url"):
            public_url = public.get("public_url")
        else:
            # If it's a string already, use it; otherwise stringify for logs
            public_url = public if isinstance(public, str) else str(public)

        print(f"[INFO] Public URL: {public_url}")
        return public_url
    except Exception as e:
        print(f"[ERROR] Supabase upload failed: {e}")
        return None


def insert_plate_record(camera_id, plate_text, confidence, plate_url, scene_url):
    """Inserts detection record into Supabase table"""
    try:
        row = {
            "camera_id": camera_id,
            "plate_text": plate_text,
            "confidence": confidence,
            "plate_url": plate_url,
            "scene_url": scene_url,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "new",
        }
        supabase.table("violations").insert(row).execute()
        return True
    except Exception as e:
        print(f"[ERROR] Supabase insert error: {e}")
        return False

# ======================================================
# API ROUTES
# ======================================================

@app.route("/")
def index():
    return jsonify({
        "status": "ok",
        "message": "Smart Parking Detection Server is running"
    })

@app.route("/test")
def test():
    return jsonify({"status": "ok", "message": "Test successful"})

@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    """Webhook endpoint for Telegram Bot - automatically processes images sent to bot"""
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
            return jsonify({"status": "ok", "message": "No photo received"}), 200
        
        # Get the largest photo (last in array)
        largest_photo = photo[-1]
        file_id = largest_photo.get("file_id")
        
        if not file_id:
            print("[TELEGRAM] No file_id in photo")
            return jsonify({"status": "ok", "message": "No file_id"}), 200
        
        print(f"[TELEGRAM] Processing photo with file_id: {file_id}")
        
        # Download image from Telegram
        img_bytes = download_image_from_telegram(file_id)
        
        # Decode image
        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        if img is None:
            print("[ERROR] Failed to decode Telegram image")
            return jsonify({"status": "error", "message": "Invalid image"}), 200
        
        print(f"[INFO] Image decoded successfully: {img.shape}")
        
        # Save raw image locally
        filename = datetime.now().strftime("%Y%m%d_%H%M%S_telegram.jpg")
        save_path = os.path.join(UPLOAD_DIR, filename)
        cv2.imwrite(save_path, img)
        print(f"[INFO] Image saved to {save_path}")
        
        # Upload original image to Supabase storage first
        camera_id = f"TELEGRAM_{chat_id}"
        original_url = upload_to_supabase_storage(save_path, camera_id)
        print(f"[INFO] Original image uploaded to Supabase: {original_url}")
        
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
                
                # Upload cropped plate to Supabase
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
        print(f"[INFO] Annotated image uploaded to Supabase: {scene_url}")
        
        # Log to database
        if not detected_plates:
            print("[INFO] No plates detected in Telegram image")
            insert_plate_record(camera_id, "no_plate_detected", 0.0, None, scene_url)
        else:
            print(f"[INFO] Logging {len(detected_plates)} plates to database")
            for dp in detected_plates:
                insert_plate_record(camera_id, dp["text"], dp["confidence"], dp.get("plate_url"), scene_url)
        
        # Clean up
        del img, annotated
        cv2.destroyAllWindows()
        
        print("[SUCCESS] Telegram webhook processed successfully\n")
        
        # Respond to Telegram (200 OK is important for webhooks)
        return jsonify({
            "status": "ok",
            "plates_detected": len(detected_plates),
            "scene_url": scene_url
        }), 200
        
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"[ERROR] Telegram webhook failed: {e}")
        print(f"[ERROR] Traceback:\n{error_details}")
        
        # Still return 200 to Telegram to avoid retries
        return jsonify({"status": "error", "message": str(e)}), 200

@app.route("/upload", methods=["GET"])
def upload_info():
    """Info page for /upload endpoint - responds to GET requests"""
    return jsonify({
        "endpoint": "/upload",
        "method": "POST",
        "status": "ready",
        "message": "This endpoint accepts POST requests with image data",
        "expected_fields": {
            "image": "multipart/form-data file (required)",
            "camera_id": "string (optional, defaults to CAM1)"
        },
        "example": "curl -X POST https://web-production-23072.up.railway.app/upload -F 'camera_id=CAM1' -F 'image=@photo.jpg'"
    })


@app.route("/upload", methods=["GET", "POST"])
def upload_image():
    """Main route: receives image or Telegram file_id, runs detection + OCR, uploads to Supabase"""
    
    # Handle GET requests - return endpoint info
    if request.method == "GET":
        return jsonify({
            "endpoint": "/upload",
            "method": "POST",
            "status": "ready",
            "message": "This endpoint accepts POST requests with image data or Telegram file_id",
            "expected_fields": {
                "telegram_file_id": "string (Telegram file_id for fetching from Telegram)",
                "image": "multipart/form-data file (for direct upload)",
                "camera_id": "string (optional, defaults to CAM1)"
            },
            "examples": [
                "curl -X POST https://your-domain/upload -H 'Content-Type: application/json' -d '{\"telegram_file_id\": \"ABC123\", \"camera_id\": \"CAM1\"}'",
                "curl -X POST https://your-domain/upload -F 'camera_id=CAM1' -F 'image=@photo.jpg'"
            ]
        }), 200
    
    # Handle POST requests - process image
    print("\n" + "="*60)
    print(f"[UPLOAD] New request received at {datetime.now()}")
    print(f"Content-Type: {request.content_type}")
    print(f"Content-Length: {request.content_length}")
    print(f"Headers: {dict(request.headers)}")
    print(f"Form data keys: {list(request.form.keys())}")
    print(f"Files keys: {list(request.files.keys())}")
    print("="*60 + "\n")
    
    try:
        # Get camera ID
        camera_id = request.form.get("camera_id") or request.headers.get("X-Camera-ID", "CAM1")
        
        # Check for JSON data (Telegram webhook format)
        if request.is_json:
            json_data = request.get_json()
            camera_id = json_data.get("camera_id", camera_id)
            telegram_file_id = json_data.get("telegram_file_id")
        else:
            telegram_file_id = request.form.get("telegram_file_id")
        
        print(f"[INFO] Camera ID: {camera_id}")

        # Get image bytes - prioritize Telegram file_id
        img_bytes = None
        source = None
        
        # Priority 1: Telegram file_id
        if telegram_file_id:
            print(f"[INFO] Telegram file_id provided: {telegram_file_id}")
            img_bytes = download_image_from_telegram(telegram_file_id)
            source = "telegram"
        # Priority 2: Multipart form data with "image" field
        elif "image" in request.files:
            print("[INFO] Image found in request.files['image']")
            img_bytes = request.files["image"].read()
            source = "direct_upload"
        # Priority 3: "file" field (alternative name)
        elif "file" in request.files:
            print("[INFO] Image found in request.files['file']")
            img_bytes = request.files["file"].read()
            source = "direct_upload"
        # Priority 4: Raw request data
        elif request.data and len(request.data) > 0:
            print("[INFO] Image found in request.data")
            img_bytes = request.data
            source = "raw_data"
        else:
            print("[ERROR] No image data or telegram_file_id found in request")
            return jsonify({
                "error": "No image data or telegram_file_id received",
                "debug": {
                    "content_type": request.content_type,
                    "form_keys": list(request.form.keys()),
                    "files_keys": list(request.files.keys()),
                    "data_length": len(request.data) if request.data else 0
                }
            }), 400

        if not img_bytes or len(img_bytes) == 0:
            print("[ERROR] Image data is empty")
            return jsonify({"error": "Empty image data received"}), 400

        print(f"[INFO] Received {len(img_bytes)} bytes of image data from {source}")

        # Decode image
        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        if img is None:
            print("[ERROR] Failed to decode image")
            return jsonify({
                "error": "Invalid image data - could not decode",
                "debug": {
                    "bytes_received": len(img_bytes),
                    "first_bytes": list(img_bytes[:20]) if len(img_bytes) >= 20 else list(img_bytes)
                }
            }), 400

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

        # If no plates were detected → still log image for debugging
        if not detected_plates:
            print("[INFO] No plates detected in image")
            insert_plate_record(camera_id, "no_plate_detected", 0.0, None, scene_url)
            return jsonify({
                "status": "no_plate_detected",
                "file": filename,
                "scene_url": scene_url,
                "message": "Image processed but no license plates found"
            }), 200

        # Log all detections to Supabase
        print(f"[INFO] Logging {len(detected_plates)} plates to database")
        for dp in detected_plates:
            insert_plate_record(camera_id, dp["text"], dp["confidence"], dp.get("plate_url"), scene_url)

        # Clean up
        del img, annotated
        cv2.destroyAllWindows()

        print("[SUCCESS] Upload processed successfully\n")
        
        return jsonify({
            "status": "ok",
            "file": filename,
            "scene_url": scene_url,
            "plates": detected_plates,
            "message": f"Successfully detected {len(detected_plates)} plate(s)"
        }), 200

    except Exception as e:
        error_details = traceback.format_exc()
        print(f"[ERROR] Upload failed: {e}")
        print(f"[ERROR] Traceback:\n{error_details}")
        
        return jsonify({
            "error": str(e),
            "type": type(e).__name__,
            "traceback": error_details if app.debug else "Enable debug mode for details"
        }), 500


# ======================================================
# ERROR HANDLERS
# ======================================================

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "File too large. Maximum size is 16MB"}), 413

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
    print(f"Starting Smart Parking Detection Server")
    print(f"Port: {port}")
    print(f"Debug: {debug_mode}")
    print(f"{'='*60}\n")
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
