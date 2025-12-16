import requests
import json

def notify_discord(webhook_url, item, search_name):
    embed = {
        "title": item["title"][:256],
        "url": item["link"],
        "color": 0x00ff99,
        "fields": [
            {
                "name": "Price",
                "value": f"${item['price']}" if item["price"] else "N/A",
                "inline": True
            },
            {
                "name": "Location",
                "value": item.get("location") or "N/A",
                "inline": True
            },
            {
                "name": "Search",
                "value": search_name,
                "inline": True
            }
        ]
    }

    if "old_price" in item:
        embed["title"] = f"📉 PRICE DROP: {embed['title']}"
        embed["color"] = 0xff9900 # Orange for updates
        embed["fields"].insert(1, {
            "name": "Old Price",
            "value": f"${item['old_price']}" if item['old_price'] else "N/A",
            "inline": True
        })

    if "old_price" in item:
        embed["title"] = f"📉 PRICE DROP: {embed['title']}"
        embed["color"] = 0xff9900 # Orange for updates
        embed["fields"].insert(1, {
            "name": "Old Price",
            "value": f"${item['old_price']}" if item['old_price'] else "N/A",
            "inline": True
        })

    if "deal_rating" in item:
        rating = item["deal_rating"]
        stats = item.get("deal_stats")
        
        emoji = "😐"
        if "Incredible" in rating: emoji = "🤯"
        elif "Great" in rating: emoji = "🤩"
        elif "Good" in rating: emoji = "🙂"
        elif "Overpriced" in rating: emoji = "💸"
        
        value_text = f"{emoji} **{rating}**"
        if stats and stats.get('average_price'):
            value_text += f"\nAvg: ${stats['average_price']} (n={stats['sample_size']})"
            
        embed["fields"].append({
            "name": "Deal Analysis",
            "value": value_text,
            "inline": False
        })

    if item.get("attributes"):
        attrs_text = "\n".join(item["attributes"])
        if len(attrs_text) > 1000:
            attrs_text = attrs_text[:1000] + "..."
        
        embed["fields"].append({
            "name": "Attributes",
            "value": attrs_text,
            "inline": False
        })

    if item.get("description"):
        desc = item["description"]
        if len(desc) > 1000:
            desc = desc[:1000] + "..."
        embed["description"] = desc

    if item.get("images") and len(item["images"]) > 0:
        embed["image"] = {"url": item["images"][0]}

    payload = {
        "username": "Craigslist Bot",
        "embeds": [embed]
    }

    res = requests.post(webhook_url, json=payload, timeout=10)
    res.raise_for_status()
