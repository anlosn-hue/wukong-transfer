# -*- coding: utf-8 -*-
# fixture = 2026-07-11 真实小红书笔记详情页的 .note-content 区块。
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from channels.playwright_channel import parse_detail_html

def test_parse_detail():
    html = (Path(__file__).parent / "fixtures" / "detail_sample.html").read_text(encoding="utf-8")
    text = parse_detail_html(html)
    assert "钱生钱的36个野路子" in text          # 来自 #detail-title
    assert "理财需谨慎" in text                   # 来自 #detail-desc 正文
    assert "钱是长了脚的" in text
