# -*- coding: utf-8 -*-
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from contract import Note, notes_to_json
import run_fetch_comments

class FakeChannel:
    def fetch_comments(self, 笔记):
        return ["我也没到账", "+1"]

def _setup(d, 高风险ids):
    notes = [Note(id=f"n{i}", 标题="t", 作者="a", 发布时间="2026-07-10",
                  点赞=99, 收藏=0, 评论=0, 链接=f"u{i}", 命中筛选=True) for i in range(4)]
    (Path(d)).mkdir(parents=True, exist_ok=True)
    (Path(d) / "清单.json").write_text(json.dumps(
        {"查询": {"关键词": "理财"}, **notes_to_json(notes)}, ensure_ascii=False), encoding="utf-8")
    (Path(d) / "研判.json").write_text(json.dumps(
        {"研判": [{"id": i, "高风险": True} for i in 高风险ids]}, ensure_ascii=False), encoding="utf-8")

def test_fetch_comments_only_highrisk_up_to_limit(tmp_path):
    _setup(str(tmp_path), ["n0", "n1", "n2"])
    out = run_fetch_comments.执行(输出目录=str(tmp_path), 台账路径=str(tmp_path/"台账.jsonl"),
        channel=FakeChannel(), 下钻上限=2, 通道名="playwright")
    files = sorted((tmp_path / "评论").glob("*.txt"))
    assert len(files) == 2                        # 高风险 3 篇但封顶 2
    assert out["下钻数"] == 2
