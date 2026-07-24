# -*- coding: utf-8 -*-
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from contract import Note, notes_to_json, notes_from_json

def test_note_roundtrip():
    n = Note(id="abc", 标题="活动没到账", 作者="小明", 发布时间="2026-07-10",
             点赞=100, 收藏=30, 评论=8, 链接="https://x/abc")
    data = notes_to_json([n])
    back = notes_from_json(data)
    assert back[0].id == "abc"
    assert back[0].点赞 == 100
    assert back[0].命中筛选 is False        # 默认未筛中
    assert back[0].筛选原因 == []
