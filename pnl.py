
import requests
import matplotlib.pyplot as plt
from dotenv import load_dotenv
import os
import google.generativeai as genai
from PIL import Image



load_dotenv()
wbrain_token = os.getenv("t")
google_api_key = os.getenv("GEMINI_API_KEY")

if not wbrain_token:
    raise ValueError("WorldQuant token 't' not found in .env file.")
if not google_api_key:
    raise ValueError("GOOGLE_API_KEY not found in .env file.")

alpha_id = 'eVn7mkO'
url = f"https://api.worldquantbrain.com/alphas/{alpha_id}/recordsets/pnl"
headers = {"Authorization": f"Bearer {wbrain_token}"}

print("Fetching PnL data from WorldQuant BRAIN...")
response = requests.get(url, headers=headers)

if response.status_code != 200:
    print("--- ERROR: Failed to fetch data from the API. ---")
    print(f"Status Code: {response.status_code}")

    print(f"Response Body: {response.text}")
    print("-----------------------------------------------------")
    print("Please check your WorldQuant token ('t' in .env) and your alpha_id.")
    exit() 

data = response.json()
pnl = data['records']

pnl_x = list(range(len(pnl)))
pnl_y = [point[1] for point in pnl]

plt.figure(figsize=(10, 6))
plt.plot(pnl_x, pnl_y, label='Original PnL', color='blue')
plt.title("PnL Curve")
plt.xlabel("Time Index")
plt.ylabel("PnL")
plt.legend()
plt.grid(True)

image_filename = "pnl_graph.jpg"
plt.savefig(image_filename, format='jpg', dpi=300, bbox_inches='tight')
plt.close()

print(f"Plot saved as '{image_filename}'")
print("-" * 30)



print("Sending image to Google Gemini for analysis...")
try:
    genai.configure(api_key=google_api_key)
    img = Image.open(image_filename)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')

    prompt = """
    Please analyze this image, which shows a financial PnL (Profit and Loss) curve.
    Provide a summary of the alpha's performance based on the graph.
    Describe the following:
    1.  The overall trend (e.g., upward, downward, sideways).
    2.  Any periods of significant growth (sharp upward slopes).
    3.  Any major drawdowns (sharp downward slopes or long periods of loss).
    4.  The general volatility of the PnL curve.
    """
    gemini_response = model.generate_content([prompt, img])
    print("\n--- Gemini AI Summary of the PnL Graph ---")
    print(gemini_response.text)
    print("------------------------------------------\n")

except Exception as e:
    print(f"\nAn error occurred while communicating with the Gemini API: {e}")