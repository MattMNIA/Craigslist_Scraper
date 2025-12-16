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

    payload = {
        "username": "Craigslist Bot",
        "embeds": [embed]
    }

    res = requests.post(webhook_url, json=payload, timeout=10)
    res.raise_for_status()
