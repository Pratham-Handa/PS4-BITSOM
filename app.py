from flask import Flask, jsonify, request
from flask_cors import CORS
import json
from pathlib import Path

# Initialize the Flask application
app = Flask(__name__)
# Enable CORS (Cross-Origin Resource Sharing) to allow our HTML page to call the API
CORS(app)

# --- Load Databases on Startup ---
# This is more efficient as data is loaded once when the server starts, not on every request.
DATA_PATH = Path("mock_data")
try:
    with open(DATA_PATH / "materials_db.json", 'r') as f:
        materials_db = json.load(f)
    with open(DATA_PATH / "recycling_infra_db.json", 'r') as f:
        recycling_infra_db = json.load(f)
    with open(DATA_PATH / "alternatives_db.json", 'r') as f:
        alternatives_db = json.load(f)
    with open(DATA_PATH / "regulations_db.json", 'r') as f:
        regulations_db = json.load(f)
    with open(DATA_PATH / "esg_sdg_db.json", 'r') as f:
        esg_sdg_db = json.load(f)
except FileNotFoundError as e:
    print(f"FATAL ERROR: A database file was not found. Please ensure the 'mock_data' directory is correct. Details: {e}")
    exit()

# --- Helper Function ---
def find_material_by_name(name):
    """Finds a material's full data object by its common name."""
    return next((mat for mat in materials_db if mat['name'].lower() == name.lower()), None)

# --- Root Endpoint for Health Check ---
@app.route('/', methods=['GET'])
def index():
    """A simple endpoint to confirm the server is running."""
    return jsonify({"status": "ok", "message": "Sustainalyze API server is running!"})

# --- API Endpoint Definition ---
@app.route('/api/analyze', methods=['GET'])
def analyze_packaging_api():
    """
    This is the core API endpoint. It expects 'material' and 'city' as query parameters.
    Example URL: http://127.0.0.1:5000/api/analyze?material=PET%20Bottle&city=Mumbai
    """
    # 1. Get parameters from the request URL
    material_name = request.args.get('material')
    city_name = request.args.get('city')

    # Basic validation
    if not material_name or not city_name:
        return jsonify({"error": "Missing 'material' or 'city' parameter"}), 400

    material = find_material_by_name(material_name)
    if not material:
        return jsonify({"error": f"Material '{material_name}' not found in database."}), 404

    city_name_lower = city_name.lower()
    mat_id = material['mat_id']

    # 2. Perform the analysis (similar logic to the original script)
    city_infra = recycling_infra_db.get(city_name_lower)
    if not city_infra:
         return jsonify({"error": f"Data for city '{city_name}' not found. Try Mumbai, Delhi, Pune, or Nagpur."}), 404

    recyclability_info = city_infra.get(mat_id, {
        "outcome": "Data Unavailable",
        "notes": "No specific recycling data for this material in this city."
    })
    sustainable_swaps = alternatives_db.get(mat_id, [])
    esg_points = esg_sdg_db.get(material['category'], [])

    # 3. Assemble and return the JSON response
    result = {
        "query": { "material": material['name'], "city": city_name.capitalize() },
        "localized_outcome": recyclability_info,
        "sustainable_alternatives": sustainable_swaps,
        "strategic_insights": {
            "esg_reporting_points": esg_points,
            "marketing_advantage": f"Highlighting a switch from {material['name']} to a sustainable alternative can improve brand perception among eco-conscious consumers.",
            "investor_relations": "Demonstrating proactive management of packaging waste strengthens ESG credentials, appealing to modern investors."
        },
        "compliance_updates": {
            "national_regulations": regulations_db
        }
    }
    
    return jsonify(result)

# --- Run the Server ---
if __name__ == '__main__':
    # Runs the Flask server on http://127.0.0.1:5000
    # The debug=True flag provides helpful error messages and auto-reloads the server on code changes.
    app.run(debug=True, port=5000)

