from filters import matches_filters

def test_filter_accepts_valid_item():
    item = {
        "title": "27 inch gaming monitor 144hz",
        "price": 250,
        "link": "test"
    }

    rules = {
        "max_price": 300,
        "keywords": {
            "include": ["gaming", "144hz"],
            "exclude": ["broken"]
        }
    }

    assert matches_filters(item, rules) is True


def test_filter_rejects_expensive_item():
    item = {
        "title": "gaming monitor",
        "price": 400,
        "link": "test"
    }

    rules = {"max_price": 300}
    assert matches_filters(item, rules) is False
