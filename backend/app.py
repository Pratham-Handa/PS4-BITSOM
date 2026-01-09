# =====================================================
# EcoStyle Agent Backend (Production Ready)
# EcoScore: Lifecycle Index (0–30)
# =====================================================

from flask import Flask, request, jsonify
from flask_cors import CORS
from transformers import pipeline
from PIL import Image
import pytesseract
import io
import random
import logging
import requests
import json
import os
import signal
import sys

# =====================================================
# ENV CONFIG
# =====================================================

SERPER_API_KEY = os.getenv("SERPER_API_KEY")

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

MAX_ECOSCORE = 30
ENV_CLAIM_BONUS = 2
WEB_VERIFICATION_BONUS = 1
WEB_VERIFICATION_CAP = 2

# =====================================================
# LOGGING
# =====================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("EcoStyleAgent")

# =====================================================
# APP INIT
# =====================================================

app = Flask(__name__)
CORS(app)

logger.info("🚀 EcoStyle Agent booting up")

# =====================================================
# LOAD AI MODEL
# =====================================================

try:
    claim_classifier = pipeline(
        "text-classification",
        model="ESGBERT/EnvironmentalBERT-environmental"
    )
    logger.info("✅ EnvironmentalBERT loaded")
except Exception as e:
    logger.error(f"❌ Failed to load EnvironmentalBERT: {e}")
    claim_classifier = None

# =====================================================
# LOAD ANCHOR PILLAR (fibers.json)
# =====================================================

with open("data/fibers.json", "r", encoding="utf-8") as f:
    material_database = json.load(f)

logger.info(f"📚 Loaded {len(material_database)} fiber entries")

# =====================================================
# OCR
# =====================================================

def extract_text_from_image(image_bytes):
    try:
        image = Image.open(io.BytesIO(image_bytes))
        return pytesseract.image_to_string(image).strip()
    except Exception as e:
        logger.error(f"❌ OCR error: {e}")
        return ""

# =====================================================
# WEB VERIFICATION (MARKET PILLAR)
# =====================================================

def run_web_verification(query):
    if not SERPER_API_KEY:
        logger.warning("⚠️ SERPER_API_KEY not set — skipping web verification")
        return []

    logger.info(f"🌐 Web search triggered: {query}")

    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {"q": query, "num": 3}

    try:
        res = requests.post(
            "https://google.serper.dev/search",
            headers=headers,
            json=payload,
            timeout=5
        )
        data = res.json()

        return [
            {
                "title": r.get("title"),
                "snippet": r.get("snippet"),
                "link": r.get("link")
            }
            for r in data.get("organic", [])
        ]

    except Exception as e:
        logger.error(f"❌ Web search failed: {e}")
        return []

# =====================================================
# ADVICE (RULE-BASED, STABLE)
# =====================================================

def generate_tip(score):
    if score >= 24:
        return "Excellent choice. Focus on durability and mindful care."
    elif score >= 18:
        return "Fairly sustainable. Washing less and air-drying helps."
    elif score >= 12:
        return "Moderate impact. Consider natural or recycled fibers."
    else:
        return "High impact. Prefer hemp, linen, or recycled materials."

# =====================================================
# OCR FALLBACK
# =====================================================

def fallback_reasoning():
    logger.warning("⚠️ OCR failed → fallback reasoning used")
    fiber = random.choice(list(material_database.values()))
    return analyze_text_core(
        f"approximate fabric detected: {fiber['displayName']}",
        fallback_used=True,
        fallback_reason="OCR confidence too low"
    )

# =====================================================
# CORE AGENT LOGIC
# =====================================================

def analyze_text_core(input_text, fallback_used=False, fallback_reason=None):

    if not claim_classifier:
        return jsonify({"error": "EnvironmentalBERT unavailable"}), 500

    logger.info(f"🧠 Reasoning on input: {input_text}")

    # EnvironmentalBERT
    bert_raw = claim_classifier(input_text)
    is_claim = any(
        r["label"] == "environmental" and r["score"] > 0.5
        for r in bert_raw
    )

    # Anchor Pillar
    matched = []
    total_score = 0

    lower = input_text.lower()
    for key, fiber in material_database.items():
        aliases = fiber.get("includes", []) + [key]
        if any(a.lower() in lower for a in aliases):
            matched.append({
                "name": fiber["displayName"],
                "ecoScore": fiber["ecoScore"],
                "certifications": fiber["certifications"],
                "biodegradable": fiber["biodegradable"],
                "recyclable": fiber["recyclable"]
            })
            total_score += fiber["ecoScore"]

    # Web search (material-based)
    web = []
    if matched:
        web = run_web_verification(
            f"{matched[0]['name']} environmental impact sustainability"
        )

    # Scoring
    if not matched:
        score = 15
    else:
        score = round(total_score / len(matched), 1)
        if is_claim:
            score += ENV_CLAIM_BONUS
        score += min(len(web), WEB_VERIFICATION_CAP)
        score = min(score, MAX_ECOSCORE)

    # Summary
    if score >= 24:
        summary = "Excellent Choice"
    elif score >= 18:
        summary = "Good Choice"
    elif score >= 12:
        summary = "Could Be Better"
    else:
        summary = "Consider Alternatives"

    return jsonify({
        "overallScore": score,
        "scoreScale": "/30",
        "summary": summary,
        "materials": matched,
        "recommendation": generate_tip(score),
        "environmentalBert": {
            "environmentalClaim": is_claim,
            "raw": bert_raw
        },
        "webVerification": web,
        "fallbackUsed": fallback_used,
        "fallbackReason": fallback_reason
    })

# =====================================================
# ROUTES
# =====================================================

@app.route("/")
def root():
    return jsonify({
        "service": "EcoStyle Agent",
        "status": "running",
        "version": "1.0"
    })

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/analyze", methods=["POST"])
def analyze_text():
    data = request.get_json()
    if not data or not data.get("text"):
        return jsonify({"error": "No text provided"}), 400
    return analyze_text_core(data["text"])

@app.route("/analyze-image", methods=["POST"])
def analyze_image():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    text = extract_text_from_image(request.files["image"].read())
    if not text:
        return fallback_reasoning()
    return analyze_text_core(text)

# =====================================================
# GRACEFUL SHUTDOWN
# =====================================================

def shutdown_handler(sig, frame):
    logger.info("🛑 EcoStyle Agent shutting down gracefully")
    sys.exit(0)

signal.signal(signal.SIGTERM, shutdown_handler)
signal.signal(signal.SIGINT, shutdown_handler)

# =====================================================
# RUN
# =====================================================

if __name__ == "__main__":
    logger.info("✅ EcoStyle Agent ready")
    app.run(host="0.0.0.0", port=10000)
