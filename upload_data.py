import os

from bs4 import BeautifulSoup
from dotenv import load_dotenv
import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch

load_dotenv()

# ---------------------------------------------------------------------------
# Config — update these
# ---------------------------------------------------------------------------
CONNECTION_STRING = os.getenv("DATABASE_URL")
INPUT_FILE = "riftbound_cards 2.xlsx"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_int(value) -> int | None:
	try:
		return int(float(str(value).strip()))
	except (ValueError, TypeError):
		return None


def parse_array(value) -> list[str] | None:
	if pd.isna(value) or not str(value).strip():
		return None
	return [v.strip() for v in str(value).split(",") if v.strip()]


def nullable(value) -> str | None:
	if pd.isna(value) or not str(value).strip():
		return None
	return str(value).strip()

# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS riftbound_cards (
	id					TEXT PRIMARY KEY,
	name				TEXT NOT NULL,
	url					TEXT NOT NULL,
	image				TEXT NOT NULL,

	energy_html			TEXT NOT NULL,
	energy_text			INTEGER NOT NULL,
	might_html			TEXT,
	might_text			INTEGER,
	domain_html			TEXT NOT NULL,
	domain_text			TEXT[] NOT NULL,
	card_type_html		TEXT NOT NULL,
	card_type_text		TEXT[] NOT NULL,
	tags_html			TEXT,
	tags_text			TEXT[],
	ability_html		TEXT NOT NULL,
	ability_text		TEXT NOT NULL,
	rarity_html			TEXT NOT NULL,
	rarity_text			TEXT NOT NULL,
	artist_html			TEXT NOT NULL,
	artist_text			TEXT NOT NULL,
	card_set_html		TEXT NOT NULL,
	card_set_text		TEXT NOT NULL,
	power_html			TEXT,
	power_text			INTEGER,
	might_bonus_html	TEXT,
	might_bonus_text	INTEGER,
	effect_html			TEXT,
	effect_text			TEXT
);
"""

INSERT_SQL = """
INSERT INTO riftbound_cards (
	id, name, url, image,
	energy_html, energy_text,
	might_html, might_text,
	domain_html, domain_text,
	card_type_html, card_type_text,
	tags_html, tags_text,
	ability_html, ability_text,
	rarity_html, rarity_text,
	artist_html, artist_text,
	card_set_html, card_set_text,
	power_html, power_text,
	might_bonus_html, might_bonus_text,
	effect_html, effect_text
) VALUES (
	%(id)s, %(name)s, %(url)s, %(image)s,
	%(energy_html)s, %(energy_text)s,
	%(might_html)s, %(might_text)s,
	%(domain_html)s, %(domain_text)s,
	%(card_type_html)s, %(card_type_text)s,
	%(tags_html)s, %(tags_text)s,
	%(ability_html)s, %(ability_text)s,
	%(rarity_html)s, %(rarity_text)s,
	%(artist_html)s, %(artist_text)s,
	%(card_set_html)s, %(card_set_text)s,
	%(power_html)s, %(power_text)s,
	%(might_bonus_html)s, %(might_bonus_text)s,
	%(effect_html)s, %(effect_text)s
)
ON CONFLICT (id) DO UPDATE SET
	name				= EXCLUDED.name,
	url					= EXCLUDED.url,
	image				= EXCLUDED.image,
	energy_html			= EXCLUDED.energy_html,
	energy_text			= EXCLUDED.energy_text,
	might_html			= EXCLUDED.might_html,
	might_text			= EXCLUDED.might_text,
	domain_html			= EXCLUDED.domain_html,
	domain_text			= EXCLUDED.domain_text,
	card_type_html		= EXCLUDED.card_type_html,
	card_type_text		= EXCLUDED.card_type_text,
	tags_html			= EXCLUDED.tags_html,
	tags_text			= EXCLUDED.tags_text,
	ability_html		= EXCLUDED.ability_html,
	ability_text		= EXCLUDED.ability_text,
	rarity_html			= EXCLUDED.rarity_html,
	rarity_text			= EXCLUDED.rarity_text,
	artist_html			= EXCLUDED.artist_html,
	artist_text			= EXCLUDED.artist_text,
	card_set_html		= EXCLUDED.card_set_html,
	card_set_text		= EXCLUDED.card_set_text,
	power_html			= EXCLUDED.power_html,
	power_text			= EXCLUDED.power_text,
	might_bonus_html	= EXCLUDED.might_bonus_html,
	might_bonus_text	= EXCLUDED.might_bonus_text,
	effect_html			= EXCLUDED.effect_html,
	effect_text			= EXCLUDED.effect_text;
"""

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def row_to_record(row) -> dict:
	return {
		"id":				str(row["id"]).strip(),
		"name":				str(row["name"]).strip(),
		"url":				str(row["url"]).strip(),
		"image":			str(row["image"]).strip(),
		"energy_html":		str(row["energy_html"]).strip(),
		"energy_text":		parse_int(row["energy_text"]),
		"might_html":		nullable(row.get("might_html")),
		"might_text":		parse_int(row.get("might_text")),
		"domain_html":		str(row["domain_html"]).strip(),
		"domain_text":		parse_array(row["domain_text"]),
		"card_type_html":	str(row["card_type_html"]).strip(),
		"card_type_text":	parse_array(row["card_type_text"]),
		"tags_html":		nullable(row.get("tags_html")),
		"tags_text":		parse_array(row.get("tags_text")),
		"ability_html":		str(row["ability_html"]).strip(),
		"ability_text":		str(row["ability_text"]).strip(),
		"rarity_html":		str(row["rarity_html"]).strip(),
		"rarity_text":		str(row["rarity_text"]).strip(),
		"artist_html":		str(row["artist_html"]).strip(),
		"artist_text":		str(row["artist_text"]).strip(),
		"card_set_html":	str(row["card_set_html"]).strip(),
		"card_set_text":	str(row["card_set_text"]).strip(),
		"power_html":		nullable(row.get("power_html")),
		"power_text":		parse_int(row.get("power_text")),
		"might_bonus_html":	nullable(row.get("might_bonus_html")),
		"might_bonus_text":	parse_int(row.get("might_bonus_text")),
		"effect_html":		nullable(row.get("effect_html")),
		"effect_text":		nullable(row.get("effect_text")),
	}


def main():

	print("[*] Connecting to PostgreSQL ...")
	conn = psycopg2.connect(CONNECTION_STRING)
	print("Connection successful!", conn.get_dsn_parameters())
	cur = conn.cursor()

	print("[*] Creating table if not exists ...")
	cur.execute(CREATE_TABLE_SQL)
	conn.commit()
	print(f"[*] Reading {INPUT_FILE} ...")
	df = pd.read_excel(INPUT_FILE)
	records = [row_to_record(row) for _, row in df.iterrows()]
	print(f"[*] {len(records)} rows loaded.")

	print("[*] Inserting records ...")
	execute_batch(cur, INSERT_SQL, records, page_size=100)
	conn.commit()

	cur.close()
	conn.close()
	print(f"[*] Done. {len(records)} records upserted into riftbound_cards.")


if __name__ == "__main__":
	main()