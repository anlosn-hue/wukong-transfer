# -*- coding: utf-8 -*-
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from channels.playwright_channel import state_path, has_login_state

def test_state_missing(tmp_path):
    assert has_login_state(str(tmp_path)) is False

def test_state_present(tmp_path):
    (tmp_path / "state.json").write_text("{}", encoding="utf-8")
    assert has_login_state(str(tmp_path)) is True
    assert state_path(str(tmp_path)).endswith("state.json")
