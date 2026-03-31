from setuptools import setup, find_packages

setup(
	name="riftbound-crawler",
	version="1.0.0",
	description="A web scraper for the Riftbound TCG card gallery",
	py_modules=["riftbound_crawler", "image_downloader"],
	install_requires=[
		"playwright",
		"pandas",
		"openpyxl",
		"requests",
		"beautifulsoup4",
				"psycopg2-binary",
				"python-dotenv",
	],
	entry_points={
		"console_scripts": [
			"riftbound-crawl=riftbound_crawler:main",
			"riftbound-images=image_downloader:main",
		],
	},
	python_requires=">=3.10",
)