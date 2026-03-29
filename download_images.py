from pathlib import Path

import requests
import pandas as pd

INPUT_FILE = "riftbound_card_resource_images.xlsx"
OUTPUT_DIR = "images"

df = pd.read_excel(INPUT_FILE)
Path(OUTPUT_DIR).mkdir(exist_ok=True)

for i, row in df.iterrows():
    url = row["image"]
    ext = Path(url.split("?")[0]).suffix or ".jpg"
    filepath = f"{OUTPUT_DIR}/{i}{ext}"

    response = requests.get(url)
    with open(filepath, "wb") as f:
        f.write(response.content)

    print(f"Downloaded: {filepath}")