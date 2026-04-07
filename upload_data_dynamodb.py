from decimal import Decimal
import os

import boto3
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
INPUT_FILE = "riftbound_cards_cleaned.xlsx"
TABLE_NAME = os.getenv("AWS_DYNAMODB_TABLE_NAME")

dynamodb = boto3.resource(
	"dynamodb",
	region_name=os.getenv("AWS_REGION"),
	aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
	aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clean_value(value):
	"""DynamoDB doesn't accept NaN/None — strip them out."""
	if pd.isna(value):
		return None
	if isinstance(value, float):
		return Decimal(str(value))  # DynamoDB doesn't accept float
	return value


def row_to_item(row) -> dict:
	item = {}
	for key, value in row.items():
		cleaned = clean_value(value)
		if cleaned is not None:		# DynamoDB doesn't accept None/null
			item[key] = cleaned
	return item

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
	print(f"[*] Reading {INPUT_FILE} ...")
	df = pd.read_excel(INPUT_FILE)
	df.columns = df.columns.str.strip()
	if "banned" in df.columns:
		df["banned"] = df["banned"].fillna(False).astype(bool)
	total = len(df)
	print(f"[*] {total} rows loaded.")

	table = dynamodb.Table(TABLE_NAME)

	# batch_writer auto-batches in groups of 25 (DynamoDB limit)
	print(f"[*] Inserting into DynamoDB table '{TABLE_NAME}' ...")
	with table.batch_writer() as batch:
		for i, (_, row) in enumerate(df.iterrows(), 1):
			item = row_to_item(row)
			batch.put_item(Item=item)
			if (i % 50 == 0) or i == total:
				print(f"    Inserted {i}/{total} ...")

	print(f"[*] Done. {total} records inserted into {TABLE_NAME}.")


if __name__ == "__main__":
	main()
