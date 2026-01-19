import json
import os
from typing import List, Dict

# Default data to initialize if file doesn't exist
DEFAULT_PRICES = [
    {
        "model": "CD70",
        "colors": "Red, Black, Blue",
        "price_excl": 134237,
        "tax": 24163,
        "levy": 1500,
        "price_incl": 159900
    },
    {
        "model": "CD70 DREAM",
        "colors": "Red, Black, Silver",
        "price_excl": 143471,
        "tax": 25826,
        "levy": 1603,
        "price_incl": 170900
    },
    {
        "model": "PRIDOR",
        "colors": "Red, Black, Blue",
        "price_excl": 177888,
        "tax": 32021,
        "levy": 1991,
        "price_incl": 211900
    },
    {
        "model": "CG125",
        "colors": "Red, Black, Blue",
        "price_excl": 200216,
        "tax": 36040,
        "levy": 2244,
        "price_incl": 238500
    },
    {
        "model": "CG125S",
        "colors": "Red, Black",
        "price_excl": 240849,
        "tax": 43354,
        "levy": 2697,
        "price_incl": 286900
    },
    {
        "model": "CG125S GOLD",
        "colors": "Red, Black",
        "price_excl": 249250,
        "tax": 44866,
        "levy": 2784,
        "price_incl": 296900
    },
    {
        "model": "CB125F",
        "colors": "Red, Black, Blue",
        "price_excl": 333205,
        "tax": 59978,
        "levy": 3717,
        "price_incl": 396900
    },
    {
        "model": "CG 150 (Red)",
        "colors": "Red",
        "price_excl": 377681,
        "tax": 67983,
        "levy": 4236,
        "price_incl": 449900
    },
    {
        "model": "CG 150 (Special)",
        "colors": "Green, 2 Tone",
        "price_excl": 386074,
        "tax": 69494,
        "levy": 4332,
        "price_incl": 459900
    },
    {
        "model": "CB150F (Std)",
        "colors": "Red, Black",
        "price_excl": 419677,
        "tax": 75542,
        "levy": 4681,
        "price_incl": 499900
    },
    {
        "model": "CB150F (Special)",
        "colors": "Silver, Blue",
        "price_excl": 423033,
        "tax": 76147,
        "levy": 4720,
        "price_incl": 503900
    }
]

class PriceManager:
    def __init__(self, filename="prices.json"):
        # Resolve path relative to this file's parent (app/utils/ -> app/../)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "../../"))
        self.filepath = os.path.join(project_root, filename)
        self.prices = []
        self.load_prices()

    def load_prices(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r') as f:
                    self.prices = json.load(f)
            except Exception as e:
                print(f"Error loading prices: {e}")
                self.prices = DEFAULT_PRICES
        else:
            self.prices = DEFAULT_PRICES
            self.save_prices()

    def save_prices(self):
        try:
            with open(self.filepath, 'w') as f:
                json.dump(self.prices, f, indent=4)
        except Exception as e:
            print(f"Error saving prices: {e}")

    def get_all(self) -> List[Dict]:
        return self.prices

    def add_price(self, price_data: Dict):
        self.prices.append(price_data)
        self.save_prices()

    def update_price(self, original_model: str, new_data: Dict):
        for i, item in enumerate(self.prices):
            if item["model"] == original_model:
                self.prices[i] = new_data
                self.save_prices()
                return True
        return False

    def delete_price(self, model_name: str):
        self.prices = [p for p in self.prices if p["model"] != model_name]
        self.save_prices()

# Singleton instance
price_manager = PriceManager()

# Helper for backward compatibility
def get_model_names():
    return [item["model"] for item in price_manager.get_all()]
