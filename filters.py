def matches_filters(item, rules):
    if rules.get("max_price") and item["price"]:
        if item["price"] > rules["max_price"]:
            return False

    title = item["title"]

    for word in rules.get("keywords", {}).get("exclude", []):
        if word.lower() in title:
            return False

    for word in rules.get("keywords", {}).get("include", []):
        if word.lower() not in title:
            return False

    return True
