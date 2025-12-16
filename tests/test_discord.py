import os
import pytest
from dotenv import load_dotenv
from notifier import notify_discord

load_dotenv()

@pytest.mark.skip(reason="Disabled by user request")
def test_discord_webhook():
    webhook = os.getenv("DISCORD_WEBHOOK_URL")
    assert webhook is not None

    notify_discord(
        webhook,
        {
            "title": "🧪 Pytest Alert",
            "price": 123,
            "link": "https://craigslist.org"
        },
        "Test Search"
    )
