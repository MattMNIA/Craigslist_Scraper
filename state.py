import json
from pathlib import Path

STATE_FILE = Path("state.json")

def load_seen():
    if STATE_FILE.exists():
        data = json.loads(STATE_FILE.read_text())
        seen_data = data.get("seen", [])
        
        # Migration: If it's a list (old format), convert to dict with None price
        if isinstance(seen_data, list):
            return {link: None for link in seen_data}
            
        # If it's a dict (new format), return it
        if isinstance(seen_data, dict):
            return seen_data
            
    return {}

def save_seen(seen):
    # seen is expected to be a dict {link: price}
    STATE_FILE.write_text(json.dumps({"seen": seen}, indent=2))
