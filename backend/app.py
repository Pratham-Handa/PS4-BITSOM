# EcoStyle Agent Backend
# Production-ready with Google Vision OCR + Explainable AI
# Python 3.10 compatible

from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import os
import json
import requests

# Google Vision
from google.cloud import vision

# Transformers (EnvironmentalBERT)
from transformers import pipeline

# -----------------------------
# Logging
# -----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("EcoStyleAgent")

# -----------------------------
# App Init
# -----------------------------
app = Flask(__name__)
CORS(app)

# -----------------------------
# Google Vision Init
# -----------------------------
vision_client = None

try:
    creds_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if creds_json:
        creds_dict = json.loads(creds_json)
        vision_client = vision.ImageAnnotatorClient.from_service_account_info(
            creds_dict
        )
        logger.info("✅ Google Vision OCR initialized")
    else:
        logger.warning("⚠️ Google Vision credentials not found")
except Exception as e:
    logger.error(f"❌ Vision init failed: {e}")

# -----------------------------
# EnvironmentalBERT Init
# -----------------------------
try:
    env_bert = pipeline(
        "text-classification",
        model="ESGBERT/EnvironmentalBERT-environmental",
        top_k=None
    )
    logger.info("✅ EnvironmentalBERT loaded")
except Exception as e:
    env_bert = None
    logger.error(f"❌ EnvironmentalBERT failed: {e}")

# -----------------------------
# Anchor Pillar (EcoScore out of 30)
# -----------------------------
FIBER_DB = {
    "cotton": 13,
    "organic cotton": 23,
    "linen": 28,
    "hemp": 28,
    "polyester": 17,
    "recycled polyester": 22,
    "viscose": 16,
    "tencel": 23,
    "lyocell": 24,
    "nylon": 14,
    "wool": 16,
    "silk": 14
}

# -----------------------------
# OCR via Google Vision
# -----------------------------
def extract_text_from_image(image_bytes):
    if not vision_client:
        return ""

    try:
        image = vision.Image(content=image_bytes)
        response = vision_client.text_detection(image=image)

        if response.error.message:
            logger.error(f"Vision API error: {response.error.message}")
            return ""

        texts = response.text_annotations
        extracted = texts[0].description if texts else ""
        logger.info("🔍 Google Vision OCR success")
        return extracted.strip()

    except Exception as e:
        logger.error(f"OCR failure: {e}")
        return ""

# -----------------------------
# Web Verification (Serper.dev optional)
# -----------------------------
def web_verification(query):
    api_key = os.environ.get("SERPER_API_KEY")
    if not api_key:
        return []

    try:
        resp = requests.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": api_key,
                "Content-Type": "application/json"
            },
            json={"q": query}
        )
        data = resp.json()
        return data.get("organic", [])[:3]
    except Exception as e:
        logger.warning(f"Web search failed: {e}")
        return []

# -----------------------------
# Core Analysis
# -----------------------------
def analyze_text_logic(text, fallback_used=False, fallback_reason=None):
    lower = text.lower()

    # Anchor Pillar
    materials = []
    scores = []

    for fiber, score in FIBER_DB.items():
        if fiber in lower:
            materials.append({
                "name": fiber,
                "ecoScore": score
            })
            scores.append(score)

    overall_score = round(sum(scores) / len(scores)) if scores else 15

    # Summary
    if overall_score >= 25:
        summary = "Excellent Choice"
    elif overall_score >= 20:
        summary = "Good Choice"
    elif overall_score >= 15:
        summary = "Could Be Better"
    else:
        summary = "Consider Alternatives"

    # EnvironmentalBERT
    bert_result = {
        "environmentalClaim": False,
        "raw": []
    }

    if env_bert:
        raw = env_bert(text)
        bert_result["raw"] = raw
        bert_result["environmentalClaim"] = any(
            r["label"].lower() == "environmental" and r["score"] > 0.5
            for r in raw
        )

    # Web Search
    web_sources = web_verification(text)

    # Tip
    if overall_score < 15:
        tip = "High environmental impact. Prefer materials like hemp, linen, or recycled fibers."
    elif overall_score < 20:
        tip = "Moderate impact. Look for certified or recycled alternatives."
    else:
        tip = "Good choice. Prefer durability and low-impact care."

    return jsonify({
        "overallScore": overall_score,
        "summary": summary,
        "recommendation": tip,
        "materials": materials,
        "environmentalBert": bert_result,
        "webVerification": web_sources,
        "fallbackUsed": fallback_used,
        "fallbackReason": fallback_reason
    })

# -----------------------------
# Routes
# -----------------------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/analyze", methods=["POST"])
def analyze_text():
    data = request.get_json()
    text = data.get("text", "").strip()

    if not text:
        return jsonify({"error": "No text provided"}), 400

    return analyze_text_logic(text)

@app.route("/analyze-image", methods=["POST"])
def analyze_image():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    image_bytes = request.files["image"].read()
    extracted = extract_text_from_image(image_bytes)

    if not extracted:
        return analyze_text_logic(
            "",
            fallback_used=True,
            fallback_reason="OCR failed, insufficient readable text"
        )

    return analyze_text_logic(extracted)

# -----------------------------
# Run
# -----------------------------
if __name__ == "__main__":
    logger.info("🚀 EcoStyle Agent running")
    app.run(host="0.0.0.0", port=5000)
