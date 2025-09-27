import json
from pathlib import Path

class PackagingAnalyzer:
    """
    A local simulator for a packaging analysis API.
    It loads data from local JSON files to mimic database queries
    and provides a comprehensive analysis for a given material and city.
    """

    def __init__(self, data_directory="mock_data"):
        """
        Initializes the analyzer by loading all data sources from a specified directory.
        """
        self.data_path = Path(data_directory)
        self._load_databases()

    def _load_databases(self):
        """Loads all the necessary JSON database files into memory."""
        print("Loading mock databases...")
        try:
            with open(self.data_path / "materials_db.json", 'r') as f:
                self.materials = json.load(f)
            with open(self.data_path / "recycling_infra_db.json", 'r') as f:
                self.infra = json.load(f)
            with open(self.data_path / "alternatives_db.json", 'r') as f:
                self.alternatives = json.load(f)
            with open(self.data_path / "regulations_db.json", 'r') as f:
                self.regulations = json.load(f)
            with open(self.data_path / "esg_sdg_db.json", 'r') as f:
                self.esg_sdg = json.load(f)
            print("All databases loaded successfully.")
        except FileNotFoundError as e:
            print(f"Error: Database file not found - {e}. Make sure you are in the correct directory.")
            exit()

    def find_material_by_name(self, name):
        """Finds a material's full data object by its common name."""
        for mat in self.materials:
            if mat['name'].lower() == name.lower():
                return mat
        return None

    def analyze_packaging(self, material_name, city_name):
        """
        The core function that simulates the API call.
        It takes a material and a city and returns a structured analysis.
        """
        material = self.find_material_by_name(material_name)
        if not material:
            return {"error": f"Material '{material_name}' not found in database."}

        city_name_lower = city_name.lower()
        mat_id = material['mat_id']

        # 1. Get localized recyclability outcome
        city_infra = self.infra.get(city_name_lower, {})
        recyclability_info = city_infra.get(mat_id, {
            "outcome": "Data Unavailable",
            "notes": "No specific recycling data for this material in this city."
        })

        # 2. Find sustainable alternatives
        sustainable_swaps = self.alternatives.get(mat_id, [])

        # 3. Gather Strategic Insights (ESG, SDG, Marketing)
        esg_points = self.esg_sdg.get(material['category'], [])

        # 4. Get relevant regulations
        relevant_regulations = self.regulations

        # 5. Assemble the final report
        result = {
            "query": {
                "material": material['name'],
                "city": city_name.capitalize()
            },
            "localized_outcome": recyclability_info,
            "sustainable_alternatives": sustainable_swaps,
            "strategic_insights": {
                "esg_reporting_points": esg_points,
                "marketing_advantage": f"Highlighting a switch from {material['name']} to a sustainable alternative can improve brand perception among eco-conscious consumers.",
                "investor_relations": "Demonstrating proactive management of packaging waste strengthens ESG credentials, appealing to modern investors."
            },
            "compliance_updates": {
                "national_regulations": relevant_regulations
            }
        }
        return result

# --- Main execution block to test the analyzer ---
if __name__ == "__main__":
    # Create an instance of the analyzer
    # It will look for the data in a sub-folder named 'mock_data'
    analyzer = PackagingAnalyzer(data_directory="mock_data")

    print("\n" + "="*50)
    print("Running Test Case 1: PET Bottle in Mumbai")
    print("="*50)
    analysis_1 = analyzer.analyze_packaging("PET Bottle", "Mumbai")
    print(json.dumps(analysis_1, indent=2))

    print("\n" + "="*50)
    print("Running Test Case 2: LDPE Film in Nagpur")
    print("(Expecting different recyclability from Mumbai)")
    print("="*50)
    analysis_2 = analyzer.analyze_packaging("LDPE Film", "Nagpur")
    print(json.dumps(analysis_2, indent=2))

    print("\n" + "="*50)
    print("Running Test Case 3: Compostable PLA Cup in Pune")
    print("(Testing a city with specific pilot infrastructure)")
    print("="*50)
    analysis_3 = analyzer.analyze_packaging("Compostable PLA Cup", "Pune")
    print(json.dumps(analysis_3, indent=2))
    
    print("\n" + "="*50)
    print("Running Test Case 4: Corrugated Cardboard in Mumbai")
    print("="*50)
    analysis_4 = analyzer.analyze_packaging("Corrugated Cardboard", "Mumbai")
    print(json.dumps(analysis_4, indent=2))
