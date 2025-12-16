from scraper import fetch_listings, parse_listing

def test_parse_listing_fields():
    rows = fetch_listings("dallas", "sya", "monitor")
    item = parse_listing(rows[0])

    assert "title" in item
    assert "link" in item
    assert isinstance(item["title"], str)
