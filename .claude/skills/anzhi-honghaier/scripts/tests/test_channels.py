# -*- coding: utf-8 -*-
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
from channels import get_channel
from channels.base import Channel

def test_get_thirdparty_stub_raises():
    ch = get_channel("thirdparty")
    assert isinstance(ch, Channel)
    with pytest.raises(NotImplementedError, match="通道②未接入"):
        ch.search_notes("理财", 时间窗天数=30)

def test_unknown_channel():
    with pytest.raises(ValueError, match="未知通道"):
        get_channel("weibo")
