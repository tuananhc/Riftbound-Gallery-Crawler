import pandas as pd
from bs4 import BeautifulSoup


def strip_html_attrs(html: str) -> str:
    """Remove style and class attributes from all HTML elements."""
    if not isinstance(html, str) or not html.strip():
        return html
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(True):
        tag.attrs.pop("style", None)
        tag.attrs.pop("class", None)
    return str(soup)


def clean_excel(input_path: str, output_path: str) -> None:
    df = pd.read_excel(input_path)

    html_cols = [col for col in df.columns if "_html" in col]

    for col in html_cols:
        df[col] = df[col].apply(strip_html_attrs)

    df.to_excel(output_path, index=False)
    print(f"Cleaned {len(html_cols)} HTML column(s): {html_cols}")
    print(f"Saved to {output_path}")


if __name__ == "__main__":
    clean_excel('riftbound_cards.xlsx', 'riftbound_cards_cleaned.xlsx')
