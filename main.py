import os
import time
import yaml
from dotenv import load_dotenv

from scraper import fetch_listings, parse_listing
from filters import matches_filters
from notifier import notify_discord
from state import load_seen, save_seen

# --------------------------------------------------
# Load environment variables
# --------------------------------------------------
load_dotenv()

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
if not WEBHOOK_URL:
    raise RuntimeError("DISCORD_WEBHOOK_URL not found in .env")

# --------------------------------------------------
# Load seen listings (deduplication)
# --------------------------------------------------
seen = load_seen()

# --------------------------------------------------
# Load search configuration
# --------------------------------------------------
with open("inputs.yaml", "r") as f:
    config = yaml.safe_load(f)

if "searches" not in config:
    raise RuntimeError("inputs.yaml must contain a 'searches' list")

# --------------------------------------------------
# Main scraping loop
# --------------------------------------------------
for search in config["searches"]:
    print(f"\n🔍 Searching: {search['name']}")

    try:
        rows = fetch_listings(
            location=search["location"],
            category=search["category"],
            query=search["query"],
            lat=search.get("lat"),
            lon=search.get("lon"),
            search_distance=search.get("search_distance")
        )
    except Exception as e:
        print(f"❌ Failed to fetch listings: {e}")
        continue

    matches_found = 0

    for row in rows:
        try:
            item = parse_listing(row)
        except Exception:
            continue

        # Skip already seen listings
        if item["link"] in seen:
            continue

        # Apply filters
        if matches_filters(item, search):
            notify_discord(WEBHOOK_URL, item, search["name"])
            seen.add(item["link"])
            matches_found += 1

            # Safety: avoid notification spam
            if matches_found >= search.get("max_alerts", 5):
                break

    print(f"✅ {matches_found} new matches")

    # Respect Craigslist (do NOT hammer)
    time.sleep(5)

# --------------------------------------------------
# Persist seen listings
# --------------------------------------------------
save_seen(seen)

