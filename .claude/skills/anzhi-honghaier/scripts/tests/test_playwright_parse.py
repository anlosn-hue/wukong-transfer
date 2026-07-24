# -*- coding: utf-8 -*-
# fixture = 2026-07-11 真实小红书搜索结果页（关键词"理财"）截取的前两张卡片。
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from channels.playwright_channel import parse_search_html

def test_parse_search_html():
    html = (Path(__file__).parent / "fixtures" / "search_sample.html").read_text(encoding="utf-8")
    notes = parse_search_html(html, 链接前缀="https://www.xiaohongshu.com")
    assert len(notes) == 2
    # 第一张卡
    assert notes[0].id == "69ec964d0000000037036426"
    assert notes[0].标题 == "普通人搞钱必看！钱生钱的36个野路子"
    assert notes[0].作者 == "凡凡的养生成长指南"
    assert notes[0].点赞 == 8107
    assert notes[0].发布时间 == "05-10"
    # 链接带 xsec_token，且以域名前缀 + /search_result/<id> 开头，可点回原帖
    assert notes[0].链接.startswith("https://www.xiaohongshu.com/search_result/69ec964d0000000037036426?xsec_token=")
    # 第二张卡
    assert notes[1].id == "6a3b9a410000000007023c40"
    assert notes[1].点赞 == 2438
    assert notes[1].发布时间 == "06-24"

def test_parse_search_html_万():
    # _to_int 处理 "1.2万" 类计数（真实高赞笔记会显示万）
    from channels.playwright_channel import _to_int
    assert _to_int("1.2万") == 12000
    assert _to_int("8107") == 8107
    assert _to_int("") == 0
