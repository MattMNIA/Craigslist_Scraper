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
                "name": "Search",
                "value": search_name,
                "inline": True
            }
        ]
    }

    payload = {
        "username": "Craigslist Bot",
        "embeds": [embed]
    }

    res = requests.post(webhook_url, json=payload, timeout=10)
    res.raise_for_status()
