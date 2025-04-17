from flask import Flask, jsonify
import requests
from datetime import datetime

app = Flask(__name__)

OZ_TO_GRAM = 31.1035
TOLA_TO_GRAM = 11.66

GOLD_API_URL = "https://data-asg.goldprice.org/dbXRates/USD"
FOREX_API_URL = "https://api.exchangerate-api.com/v4/latest/USD"

HEADERS = {
    'User-Agent': 'Mozilla/5.0',
    'Accept': 'application/json'
}

def fetch_prices():
    try:
        gold_res = requests.get(GOLD_API_URL, headers=HEADERS).json()
        forex_res = requests.get(FOREX_API_URL).json()
        usd_to_pkr = forex_res['rates']['PKR']

        item = gold_res['items'][0]
        gold_oz = item['xauPrice']
        silver_oz = item['xagPrice']

        # Gold conversions
        gold_g = gold_oz / OZ_TO_GRAM
        gold_tola = gold_g * TOLA_TO_GRAM

        # Silver conversions
        silver_g = silver_oz / OZ_TO_GRAM
        silver_tola = silver_g * TOLA_TO_GRAM

        return {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "usd_to_pkr": usd_to_pkr,
            "gold": {
                "oz": round(gold_oz, 2),
                "g": round(gold_g, 2),
                "tola": round(gold_tola, 2),
                "oz_pkr": round(gold_oz * usd_to_pkr, 2),
                "g_pkr": round(gold_g * usd_to_pkr, 2),
                "tola_pkr": round(gold_tola * usd_to_pkr, 2),
            },
            "silver": {
                "oz": round(silver_oz, 2),
                "g": round(silver_g, 2),
                "tola": round(silver_tola, 2),
                "oz_pkr": round(silver_oz * usd_to_pkr, 2),
                "g_pkr": round(silver_g * usd_to_pkr, 2),
                "tola_pkr": round(silver_tola * usd_to_pkr, 2),
            }
        }

    except Exception as e:
        return {"error": str(e)}

@app.route("/")
def index():
    return jsonify(fetch_prices())

if __name__ == "__main__":
    app.run(debug=True)
