import pandas as pd
from bs4 import BeautifulSoup

df = pd.read_excel("riftbound_cards.xlsx")
images = []

def extract_srcs(html):
	if pd.isna(html):
		return []
	soup = BeautifulSoup(html, "html.parser")
	return [img["src"].split("?")[0] for img in soup.find_all("img")]

for _, row in df.iterrows():
	for key in row.index:
		if "html" in key and row[key] and isinstance(row[key], str) and "<img" in row[key]:
			images.extend(extract_srcs(row[key]))

images = list(set(images))  # Remove duplicates
    
pd.DataFrame({"image": images}).to_excel("riftbound_card_resource_images.xlsx", index=False)