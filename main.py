import os
import time
import yaml
from dotenv import load_dotenv

from scraper import fetch_listings, parse_listing, fetch_details, parse_details
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
config_path = "inputs.yaml"
if not os.path.exists(config_path):
    print("⚠️ inputs.yaml not found, using inputs.example.yaml")
    config_path = "inputs.example.yaml"

with open(config_path, "r") as f:
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

        # Check if seen and price changed
        is_seen = item["link"] in seen
        price_changed = False
        old_price = None
        
        if is_seen:
            old_price = seen[item["link"]]
            # If price has changed, we treat it as a candidate for update
            if old_price != item["price"]:
                price_changed = True
                print(f"  -> Price change detected for {item['title']}: {old_price} -> {item['price']}")
        
        # Skip if seen and price hasn't changed
        if is_seen and not price_changed:
            continue

        # Apply filters
        if matches_filters(item, search):
            # Update seen with new price
            seen[item["link"]] = item["price"]

            # Deep fetch for more details
            print(f"  -> Deep fetching: {item['title']}")
            try:
                soup = fetch_details(item["link"])
                details = parse_details(soup)
                item.update(details)
                
                # Add price change info to item for notification
                if price_changed and old_price is not None:
                    item["old_price"] = old_price
                    
                time.sleep(1) # Be nice to the server
            except Exception as e:
                print(f"⚠️ Failed to fetch details: {e}")

            notify_discord(WEBHOOK_URL, item, search["name"])
            matches_found += 1

    print(f"✅ {matches_found} new matches")

    # Respect Craigslist (do NOT hammer)
    time.sleep(5)

# --------------------------------------------------
# Persist seen listings
# --------------------------------------------------
save_seen(seen)

