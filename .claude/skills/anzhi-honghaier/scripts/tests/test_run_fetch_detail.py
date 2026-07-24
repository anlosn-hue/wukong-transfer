# -*- coding: utf-8 -*-
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from contract import Note, notes_to_json
import run_fetch_detail

class FakeChannel:
    def fetch_detail(self, 笔记):
        return f"正文-{笔记.id}"

def _write_清单(d):
    notes = [Note(id=f"n{i}", 标题="理财未到账", 作者="a", 发布时间="2026-07-10",
                  点赞=99, 收藏=0, 评论=0, 链接=f"u{i}", 命中筛选=True, 筛选原因=["风险词:未到账"])
             for i in range(3)]
    notes.append(Note(id="miss", 标题="天气", 作者="b", 发布时间="2026-07-10",
                      点赞=1, 收藏=0, 评论=0, 链接="um", 命中筛选=False))
    payload = {"查询": {"关键词": "理财"}, **notes_to_json(notes)}
    (Path(d) / "清单.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

def test_fetch_only_hits_up_to_limit(tmp_path):
    _write_清单(str(tmp_path))
    out = run_fetch_detail.执行(输出目录=str(tmp_path), 台账路径=str(tmp_path/"台账.jsonl"),
        channel=FakeChannel(), 抓取上限=2, 通道名="playwright")
    files = sorted((tmp_path / "正文").glob("*.txt"))
    assert len(files) == 2                       # 只抓命中的、且封顶 2
    assert out["抓取数"] == 2
    assert "miss" not in [f.stem for f in files] # 未命中的不抓

def test_session_cap_stops_early(tmp_path):
    _write_清单(str(tmp_path))                   # 清单.json 已存在 → 会话抓取数从 1 起
    out = run_fetch_detail.执行(输出目录=str(tmp_path), 台账路径=str(tmp_path/"台账.jsonl"),
        channel=FakeChannel(), 抓取上限=10, 通道名="playwright", 会话上限=2)
    # 会话数：起始1（搜索）→抓1篇变2→触顶停；只抓到 1 篇
    assert out["抓取数"] == 1
    assert "会话抓取上限" in out["中断"]
