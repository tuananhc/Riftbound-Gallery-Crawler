import asyncio
from pathlib import Path

import pandas as pd
from playwright.async_api import async_playwright, Page, BrowserContext, TimeoutError as PlaywrightTimeout

BASE_URL = "https://riftbound.leagueoflegends.com/en-us/card-gallery"
OUTPUT_FILE = "riftbound_cards.xlsx"
MAX_CONCURRENT = 10  # Number of tabs open simultaneously

def clean(text: str | None) -> str | None:
	"""Strip whitespace; return None for empty strings."""
	if text is None:
		return None
	text = text.strip()
	return text if text else None

async def load_all_cards(page: Page) -> None:
	"""
	Click any 'Load More' / 'Show More' button repeatedly until it disappears,
	then fall back to full-page scrolling for infinite-scroll galleries.
	"""
	try:
		filter_btn = page.locator('button:has-text("Show Filters")')
		await filter_btn.click()
		set_filter_btn = page.locator('button[data-testid="card-sets-trigger"]')
		await set_filter_btn.click()
		btn = page.locator('#card-sets-radio-group-item-all')
		if await btn.is_visible(timeout=2000):
			await btn.click()
			await page.wait_for_load_state("networkidle", timeout=10_000)
	except PlaywrightTimeout:
		pass

async def extract_card_from_element(page: Page) -> dict:
	"""Extract all available attributes from a single card element."""
	card = {}

	card_el = page.locator(("div[data-testid='frame'] > div > div"))
	card_el = await card_el.all()
	header = card_el[0]
	details = card_el[1]

	card["name"] = await header.locator("h3").inner_text()
	card["id"] = await header.locator("p").inner_text()
	card["url"] = page.url

	card["image"] = await (details.locator("div.innerWrapper img")).get_attribute("src")
	card_details = await details.locator("div:has(> h6)").all()
	for card_detail in card_details:
		key = await card_detail.locator("h6").inner_text()
		value = await card_detail.locator("div:has(> p)").all()
		if len(value) == 1:
			value_html = await value[0].inner_html()
			value_text = await value[0].inner_text()
		else:
			value_html = [await v.inner_html() for v in value]
			value_html = ", ".join(value_html)
			value_text = [await v.inner_text() for v in value]
			value_text = ", ".join(value_text)
		key = key.lower().replace(" ", "_")
		card[key + "_html"] = value_html
		card[key + "_text"] = value_text

	return card

async def fetch_card(
	index: int,
	card_url: str,
	context: BrowserContext,
	semaphore: asyncio.Semaphore,
	total: int,
) -> dict:
	"""Open a new tab, scrape one card, close the tab. Bounded by semaphore."""
	async with semaphore:
		new_page = await context.new_page()
		try:
			await new_page.goto('https://riftbound.leagueoflegends.com/en-us/card-gallery/' + card_url, wait_until="networkidle", timeout=30_000)
			card_data = await extract_card_from_element(new_page)
			if (index % 50 == 0) or index == total:
				print(f"    Extracted {index}/{total} cards …")
			return card_data
		except Exception as e:
			print(f"    [!] Error on card {index}: {e}")
			return {"error": str(e), "index": index}
		finally:
			await new_page.close()


async def crawl(
	visit_details: bool = False,
	headless: bool = True,
	output: str = OUTPUT_FILE,
	max_concurrent: int = MAX_CONCURRENT,
) -> list[dict]:
	"""
	Main entry point.

	Args:
		visit_details:  If True, follows each card's detail link for richer data.
		headless:       Run browser in headless mode.
		output:         Path to write the results.
		max_concurrent: Max number of card detail tabs open at once.
	"""
	async with async_playwright() as p:
		browser = await p.chromium.launch(headless=headless)
		context = await browser.new_context(
			user_agent=(
				"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
				"AppleWebKit/537.36 (KHTML, like Gecko) "
				"Chrome/124.0.0.0 Safari/537.36"
			),
			viewport={"width": 1440, "height": 900},
		)
		page = await context.new_page()

		print(f"[*] Navigating to {BASE_URL} …")
		await page.goto(BASE_URL, wait_until="networkidle", timeout=60_000)

		print("[*] Loading all cards (scrolling / clicking 'Load More') …")
		await load_all_cards(page)

		card_elements = await page.locator("div[data-testid='card-grid'] > a").all()
		total = len(card_elements)
		print(f"[*] Found {total} card elements. Extracting with {max_concurrent} concurrent tabs …")

		# Collect all hrefs first (while gallery page is still open)
		card_urls = [await el.get_attribute("href") for el in card_elements]
		semaphore = asyncio.Semaphore(max_concurrent)
		tasks = [
			fetch_card(i, url, context, semaphore, total)
			for i, url in enumerate(card_urls, 1)
			if url
		]
		cards: list[dict] = list(await asyncio.gather(*tasks))

		await browser.close()

	# Deduplicate by name (keep first occurrence)
	seen: set[str] = set()
	unique: list[dict] = []
	for card in cards:
		key = card.get("link") or str(card.get("id"))
		if key not in seen:
			seen.add(key)
			unique.append(card)

	print(f"\n[*] {len(unique)} unique cards extracted (was {len(cards)} before dedup).")

	# Write output
	out_path = Path(output)
	pd.DataFrame(unique).to_excel(output, index=False)
	print(f"[*] Saved to {out_path.resolve()}")

	return unique

async def test_crawl():
	"""Run a quick test crawl to verify everything works end-to-end."""
	async with async_playwright() as p:
		browser = await p.chromium.launch(headless=True)
		context = await browser.new_context()
		page = await context.new_page()
		await page.goto('https://riftbound.leagueoflegends.com/en-us/card-gallery/#card-gallery--sfd-192-221', wait_until="networkidle", timeout=60_000)
		card_data = await extract_card_from_element(page)
		print(card_data)
		await browser.close()

# Entry point
if __name__ == "__main__":
	import argparse

	parser = argparse.ArgumentParser(description="Riftbound card gallery crawler")
	parser.add_argument("--details", action="store_true", help="Visit each card's detail page for richer data (slower)")
	parser.add_argument("--no-headless", action="store_true", help="Show the browser window (useful for debugging)")
	parser.add_argument("--output", default=OUTPUT_FILE, help=f"Output JSON file (default: {OUTPUT_FILE})")
	parser.add_argument("--concurrency", type=int, default=MAX_CONCURRENT, help=f"Max concurrent tabs (default: {MAX_CONCURRENT})")
	args = parser.parse_args()

	asyncio.run(
		# crawl(
		# 	visit_details=args.details,
		# 	headless=not args.no_headless,
		# 	output=args.output,
		# 	max_concurrent=args.concurrency,
		# )
		test_crawl()
	)
