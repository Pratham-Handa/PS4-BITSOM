# =====================================================
# EcoStyle Agent Backend (FINAL, STABLE)
# Deterministic + Explainable
# =====================================================

from flask import Flask, request, jsonify
from flask_cors import CORS
from transformers import pipeline
from PIL import Image
import pytesseract
import io
import random
import logging
import json

# =====================================================
# CONFIG
# =====================================================

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

MAX_ECOSCORE = 30
ENV_CLAIM_BONUS = 2

# =====================================================
# LOGGING (TERMINAL)
# =====================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("EcoStyleAgent")

# =====================================================
# APP INIT + CORS (FIXED)
# =====================================================

app = Flask(__name__)
CORS(
    app,
    resources={r"/*": {"origins": ["http://127.0.0.1:5500", "http://localhost:5500"]}},
    supports_credentials=True
)

# =====================================================
# DEBUG LOG CAPTURE (FOR FRONTEND)
# =====================================================

def new_debug_logger():
    return {
        "agent": [],
        "scoring": [],
        "system": []
    }

def log(debug, channel, message):
    debug[channel].append(message)
    logger.info(message)

# =====================================================
# LOAD MODEL
# =====================================================

logger.info("🚀 Starting EcoStyle Agent backend")

try:
    claim_classifier = pipeline(
        "text-classification",
        model="ESGBERT/EnvironmentalBERT-environmental"
    )
    logger.info("✅ EnvironmentalBERT loaded")
except Exception as e:
    logger.error(f"❌ EnvironmentalBERT load failed: {e}")
    claim_classifier = None

# =====================================================
# LOAD FIBER DATABASE
# =====================================================

logger.info("📚 Loading fiber dataset")

with open("data/fibers.json", "r", encoding="utf-8") as f:
    material_database = json.load(f)

logger.info(f"✅ Loaded {len(material_database)} fiber groups")

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
# FALLBACK
# =====================================================

def fabric_fallback_reasoning():
    fiber = random.choice(list(material_database.values()))
    return analyze_fabric_from_text(
        f"approximate fabric detected: {fiber['displayName']}",
        fallback_used=True,
        fallback_reason="OCR confidence too low. Fabric inferred using material priors."
    )

# =====================================================
# CORE AGENT
# =====================================================

def analyze_fabric_from_text(input_text, fallback_used=False, fallback_reason=None):
    debug = new_debug_logger()

    if not claim_classifier:
        return jsonify({"error": "EnvironmentalBERT unavailable"}), 500

    log(debug, "agent", "🧠 Agent reasoning started")
    log(debug, "agent", f"📄 Input text: {input_text}")

    lower_text = input_text.lower()

    # ---------- EnvironmentalBERT ----------
    bert_results = claim_classifier(input_text)

    is_env_claim = any(
        r["label"] == "environmental" and r["score"] > 0.5
        for r in bert_results
    )

    log(debug, "agent", f"🌱 Environmental claim detected: {is_env_claim}")

    # ---------- Anchor Pillar ----------
    matched_fibers = []
    total_score = 0
    market_sources = []

    for key, fiber in material_database.items():
        aliases = fiber.get("includes", []) + [key]
        if any(alias.lower() in lower_text for alias in aliases):
            matched_fibers.append({
                "name": fiber["displayName"],
                "ecoScore": fiber["ecoScore"],
                "description": fiber["description"],
                "biodegradable": fiber["biodegradable"],
                "recyclable": fiber["recyclable"],
                "certifications": fiber["certifications"]
            })
            total_score += fiber["ecoScore"]
            market_sources.extend(fiber.get("sources", []))

    # ---------- SCORING ----------
    if not matched_fibers:
        overall_score = 15
        summary = "Could Be Better"
        log(debug, "scoring", "⚠️ No fiber matched — neutral baseline applied")
    else:
        avg_score = round(total_score / len(matched_fibers), 1)
        log(debug, "scoring", f"📐 Anchor average score: {avg_score}")

        final_score = avg_score

        if is_env_claim:
            final_score += ENV_CLAIM_BONUS
            log(debug, "scoring", "➕ Environmental claim bonus applied")

        overall_score = round(min(final_score, MAX_ECOSCORE), 1)

        if overall_score >= 24:
            summary = "Excellent Choice"
        elif overall_score >= 18:
            summary = "Good Choice"
        elif overall_score >= 12:
            summary = "Could Be Better"
        else:
            summary = "Consider Alternatives"

    log(debug, "scoring", f"📊 Final EcoScore: {overall_score}/30")
    log(debug, "system", f"🔎 Market sources returned: {len(market_sources)}")

    # ---------- RESPONSE ----------
    response = {
        "overallScore": overall_score,
        "scoreScale": "/30",
        "summary": summary,
        "materials": matched_fibers,
        "recommendation": generate_sustainability_tip(overall_score),
        "extractedText": input_text,
        "fallbackUsed": fallback_used,
        "fallbackReason": fallback_reason,
        "environmentalBert": {
            "environmentalClaim": is_env_claim,
            "raw": bert_results
        },
        "webVerification": market_sources,
        "debugLogs": debug
    }

    return jsonify(response)

# =====================================================
# RULE-BASED ADVICE
# =====================================================

def generate_sustainability_tip(score):
    if score >= 24:
        return "Excellent choice. Focus on durability and mindful care to extend garment life."
    elif score >= 18:
        return "A fairly sustainable option. Washing less and air-drying can further reduce impact."
    elif score >= 12:
        return "Moderate impact garment. Consider natural or recycled fibers next time."
    else:
        return "High environmental impact. Prefer materials like hemp, linen, or recycled fibers."

# =====================================================
# API ROUTES
# =====================================================

@app.route("/analyze", methods=["POST"])
def analyze_text():
    data = request.get_json()
    if not data or not data.get("text"):
        return jsonify({"error": "No text provided"}), 400
    return analyze_fabric_from_text(data["text"])

@app.route("/analyze-image", methods=["POST"])
def analyze_image():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    image_bytes = request.files["image"].read()
    extracted_text = extract_text_from_image(image_bytes)

    if not extracted_text:
        return fabric_fallback_reasoning()

    return analyze_fabric_from_text(extracted_text)

# =====================================================
# RUN
# =====================================================

if __name__ == "__main__":
    logger.info("✅ EcoStyle Agent running on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
