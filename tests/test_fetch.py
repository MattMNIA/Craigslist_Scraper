from scraper import fetch_listings

def test_fetch_listings_returns_results():
    rows = fetch_listings(
        location="dallas",
        category="sya",
        query="monitor"
    )
    assert len(rows) > 0
