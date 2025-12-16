import pytest
from scraper import fetch_listings

@pytest.mark.integration
def test_fetch_listings_live():
    rows = fetch_listings("dallas", "sya", "monitor")
    assert len(rows) > 0

@pytest.mark.integration
def test_fetch_listings_with_geo_search():
    rows = fetch_listings(
        location="ames",
        category="sya",
        query="monitor",
        lat=42.0205,
        lon=-93.6202,
        search_distance=72
    )
    assert isinstance(rows, list)
