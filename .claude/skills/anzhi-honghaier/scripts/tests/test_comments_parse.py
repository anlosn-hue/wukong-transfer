# -*- coding: utf-8 -*-
# fixture = 2026-07-11 真实小红书笔记页的前 4 条 .comment-item。
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from channels.playwright_channel import parse_comments_html

def test_parse_comments():
    html = (Path(__file__).parent / "fixtures" / "comments_sample.html").read_text(encoding="utf-8")
    cs = parse_comments_html(html)
    assert len(cs) == 4
    assert "赚穷人的钱靠骗" in cs[0]
    assert all(c.strip() for c in cs)     # 无空评论
