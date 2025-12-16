# test_discord.py
import sys
import os

# Add parent directory to path to allow importing modules from root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from notifier import notify_discord
from dotenv import load_dotenv

load_dotenv()
notify_discord(
    f"{os.getenv('DISCORD_WEBHOOK_URL')}",
    {
        "title": "Test Listing",
        "price": 123,
        "link": "https://craigslist.org"
    },
    "Test Search"
)
