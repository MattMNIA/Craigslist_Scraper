import json
from pathlib import Path

STATE_FILE = Path("state.json")

def load_seen():
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text())["seen"])
    return set()

def save_seen(seen):
    STATE_FILE.write_text(json.dumps({"seen": list(seen)}, indent=2))
