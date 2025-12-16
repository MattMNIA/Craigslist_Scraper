from state import load_seen, save_seen

def test_state_round_trip(tmp_path, monkeypatch):
    fake_state = tmp_path / "state.json"

    monkeypatch.setattr("state.STATE_FILE", fake_state)

    seen = load_seen()
    seen.add("https://example.com/item")

    save_seen(seen)

    reloaded = load_seen()
    assert "https://example.com/item" in reloaded
