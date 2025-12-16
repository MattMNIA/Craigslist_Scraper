import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; personal-scraper/1.0)"
}

def fetch_listings(location, category, query):
    params = {"query": query}
    url = f"https://{location}.craigslist.org/search/{category}?{urlencode(params)}"
    res = requests.get(url, headers=HEADERS, timeout=10)
    res.raise_for_status()

    soup = BeautifulSoup(res.text, "html.parser")
    return soup.select(".result-row")
def parse_listing(row):
    title = row.select_one(".result-title").text.strip()
    link = row.select_one(".result-title")["href"]
    price_el = row.select_one(".result-price")
    price = int(price_el.text.replace("$", "")) if price_el else None

    return {
        "title": title.lower(),
        "price": price,
        "link": link,
    }

