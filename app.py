# EcoStyle Agent Backend
# This script sets up a simple web server to host the AI models.
# To run this:
# 1. Make sure you have Python installed.
# 2. Install the necessary libraries:
#    pip install Flask transformers torch flask-cors sentencepiece
# 3. Run the script from your terminal: python app.py

from flask import Flask, request, jsonify
from flask_cors import CORS
from transformers import pipeline
import torch # Even if not used directly, it's needed by transformers

# Initialize the Flask application
app = Flask(__name__)
# Enable Cross-Origin Resource Sharing (CORS) to allow your HTML file to call this server
CORS(app)

# --- LOAD MODELS ---
# It's best to load the models once when the server starts.
# This avoids reloading them on every request, which is very slow.
print("Loading models... This may take a few minutes.")
try:
    # 1. Environmental Claim Classifier
    claim_classifier = pipeline(
        "text-classification", 
        model="ESGBERT/EnvironmentalBERT-environmental"
    )

    # 2. Sustainable Fashion Advice Generator
    # NOTE: The previous model (distilgpt2) was providing low-quality responses.
    # Switching to t5-small, a model designed for text-to-text tasks like summarization and advice generation.
    # This will produce more relevant and coherent tips, while still running efficiently on a CPU.
    advice_generator = pipeline(
        "text2text-generation", 
        model="t5-small"
    )
    print("Models loaded successfully!")
except Exception as e:
    print(f"Error loading models: {e}")
    print("The backend will not function correctly without the models.")
    claim_classifier = None
    advice_generator = None


# --- KNOWLEDGE BASE ---
# This is your database of material properties, simulating TextileNet + Carbon Data.
# In a real application, this would likely be in a separate database file.
material_database = {
    'organic cotton': {'score': 90, 'pros': ['Uses no synthetic pesticides', 'Reduces water pollution'], 'cons': ['Still requires significant water to grow']},
    'cotton': {'score': 50, 'pros': ['Natural, biodegradable fiber'], 'cons': ['Very high water consumption', 'Heavy pesticide use in conventional farming']},
    'recycled polyester': {'score': 75, 'pros': ['Reduces plastic waste from landfills', 'Lower carbon footprint than virgin polyester'], 'cons': ['Can release microplastics when washed']},
    'polyester': {'score': 20, 'pros': ['Durable and water-resistant'], 'cons': ['Made from fossil fuels (non-renewable)', 'Not biodegradable', 'Energy-intensive production']},
    'linen': {'score': 95, 'pros': ['Made from flax plant, very durable', 'Requires minimal water and pesticides', 'Fully biodegradable'], 'cons': ['Can wrinkle easily']},
    'hemp': {'score': 98, 'pros': ['Extremely durable natural fiber', 'Requires no pesticides and little water', 'Improves soil health'], 'cons': ['Limited availability currently']},
    'tencel': {'score': 85, 'pros': ['Made from sustainable wood pulp', 'Produced in a closed-loop system recycling water'], 'cons': ['Chemical processing is required']},
    'spandex': {'score': 15, 'pros': ['Provides stretch and comfort'], 'cons': ['Synthetic fiber derived from petroleum', 'Not biodegradable']},
    'viscose': {'score': 40, 'pros': ['Made from wood pulp'], 'cons': ['Can contribute to deforestation if not sourced responsibly', 'Chemically intensive process']},
}


# --- API ENDPOINT ---
# This is the core function that your frontend will call.
@app.route('/analyze', methods=['POST'])
def analyze_fabric():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    input_text = data.get('text')

    if not input_text:
        return jsonify({"error": "No text provided"}), 400
        
    if not claim_classifier or not advice_generator:
        return jsonify({"error": "Models are not loaded. Cannot perform analysis."}), 500

    # --- AI PIPELINE ---

    # 1. Classify if the text contains an environmental claim
    claim_results = claim_classifier(input_text)
    is_environmental_claim = any(res['label'] == 'environmental' and res['score'] > 0.5 for res in claim_results)

    # 2. Extract materials and calculate score
    lower_input = input_text.lower()
    materials_found = []
    total_score = 0
    material_count = 0

    for material, details in material_database.items():
        if material in lower_input:
            materials_found.append({"name": material, **details})
            total_score += details['score']
            material_count += 1
            
    # Add bonus points if a general environmental claim was detected
    if is_environmental_claim and material_count > 0:
        total_score += 5 * material_count # Add a small bonus
        total_score = min(total_score, 100 * material_count) # Cap the score

    overall_score = round(total_score / material_count) if material_count > 0 else 45

    # 3. Generate user-friendly advice
    analysis_for_prompt = f"A garment with an overall sustainability score of {overall_score}/100. "
    if materials_found:
        material_names = ", ".join([m['name'] for m in materials_found])
        analysis_for_prompt += f"It contains: {material_names}. "
    
    # T5 models work best with a task-specific prefix in the prompt.
    prompt = f"give a short, encouraging sustainable fashion tip based on the following analysis: {analysis_for_prompt}"
    
    generated_outputs = advice_generator(prompt, max_length=100, num_return_sequences=1)
    # text2text models don't repeat the prompt in the output, so we can use the generated text directly.
    recommendation = generated_outputs[0]['generated_text'].strip()

    # Determine summary text based on score
    if overall_score >= 85:
        summary = 'Excellent Choice'
    elif overall_score >= 60:
        summary = 'Good Choice'
    elif overall_score >= 40:
        summary = 'Could Be Better'
    else:
        summary = 'Consider Alternatives'
        
    # --- CONSTRUCT RESPONSE ---
    response_data = {
        "overallScore": overall_score,
        "summary": summary,
        "materials": materials_found,
        "recommendation": recommendation
    }

    return jsonify(response_data)

# This allows the script to be run directly
if __name__ == '__main__':
    # The server will run on http://127.0.0.1:5000
    app.run(debug=True, port=5000)

