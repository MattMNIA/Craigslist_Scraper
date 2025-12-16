import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode
from logger import get_logger

logger = get_logger("scraper")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; personal-scraper/1.0)"
}

def fetch_listings(location, category, query, lat=None, lon=None, search_distance=None):
    params = {"query": query}
    
    if lat and lon and search_distance:
        params.update({
            "lat": lat,
            "lon": lon,
            "search_distance": search_distance
        })

    url = f"https://{location}.craigslist.org/search/{category}?{urlencode(params)}"

    logger.info(f"Fetching URL: {url}")

    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
    except Exception as e:
        logger.exception("Request failed")
        raise

    logger.debug(f"Status Code: {res.status_code}")
    logger.debug(f"Final URL: {res.url}")
    logger.debug(f"Response Headers: {dict(res.headers)}")
    logger.debug(f"Response Length: {len(res.text)} bytes")

    # Log suspicious responses
    if res.status_code != 200:
        logger.warning(f"Non-200 response: {res.status_code}")

    if "captcha" in res.text.lower():
        logger.error("CAPTCHA detected in response")

    soup = BeautifulSoup(res.text, "html.parser")
    rows = soup.select(".cl-static-search-result")

    logger.info(f"Found {len(rows)} result rows")

    # Save raw HTML if parsing fails
    if len(rows) == 0:
        html_path = f"logs/empty_response_{location}_{category}_{query}.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(res.text)
        logger.error(f"No results parsed — HTML saved to {html_path}")

    return rows

def parse_listing(row):
    try:
        anchor = row.find("a")
        if not anchor:
            raise ValueError("No anchor found in row")
            
        link = anchor["href"]
        
        title_el = row.select_one(".title")
        title = title_el.text.strip().lower() if title_el else "unknown"

        price_el = row.select_one(".price")
        price = None
        if price_el:
            price_text = price_el.text.replace("$", "").replace(",", "").strip()
            if price_text.isdigit():
                price = int(price_text)

        location_el = row.select_one(".location")
        location = location_el.text.strip() if location_el else None

        return {
            "title": title,
            "price": price,
            "link": link,
            "location": location,
        }

    except Exception:
        logger.exception("Failed to parse listing row")
        raise

