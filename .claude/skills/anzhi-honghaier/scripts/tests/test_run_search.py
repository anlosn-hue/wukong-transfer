# -*- coding: utf-8 -*-
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from contract import Note
import run_search

class FakeChannel:
    def search_notes(self, kw, *, 时间窗天数):
        # 发布时间留空 → funnel 时间窗"不误杀"，测试不随运行日期漂移
        return [Note(id="n1", 标题="理财未到账", 作者="a", 发布时间="",
                     点赞=99, 收藏=0, 评论=0, 链接="u1"),
                Note(id="n2", 标题="天气不错", 作者="b", 发布时间="",
                     点赞=1, 收藏=0, 评论=0, 链接="u2")]

def test_run_search_writes_清单(tmp_path):
    out = run_search.执行(
        关键词="理财", 时间窗天数=30, 输出目录=str(tmp_path),
        台账路径=str(tmp_path / "台账.jsonl"),
        channel=FakeChannel(),
        风险语气词=["未到账"], 互动阈值={"点赞": 50, "收藏": 20, "评论": 5},
        单日上限=20)
    data = json.loads((tmp_path / "清单.json").read_text(encoding="utf-8"))
    hits = [n for n in data["笔记"] if n["命中筛选"]]
    assert len(hits) == 1 and hits[0]["id"] == "n1"
    assert out["命中数"] == 1
    assert (tmp_path / "台账.jsonl").exists()

def test_run_search_cap_blocks(tmp_path):
    lp = tmp_path / "台账.jsonl"
    import ledger
    # 20 条 A 层条目 = 20 次查询，达单日上限
    for _ in range(20):
        ledger.record_query(str(lp), 关键词="x", 通道="playwright", 层级="A", 抓取量=1)
    out = run_search.执行(关键词="理财", 时间窗天数=30, 输出目录=str(tmp_path),
        台账路径=str(lp), channel=FakeChannel(),
        风险语气词=["未到账"], 互动阈值={"点赞": 50, "收藏": 20, "评论": 5}, 单日上限=20)
    assert out["拒绝"] is True and "单日上限" in out["原因"]

def test_run_search_cap_ignores_BC(tmp_path):
    lp = tmp_path / "台账.jsonl"
    import ledger
    # 20 条 B/C 层条目不应算作查询次数 → 不拒绝
    for _ in range(20):
        ledger.record_query(str(lp), 关键词="x", 通道="playwright", 层级="B", 抓取量=1)
    out = run_search.执行(关键词="理财", 时间窗天数=30, 输出目录=str(tmp_path),
        台账路径=str(lp), channel=FakeChannel(),
        风险语气词=["未到账"], 互动阈值={"点赞": 50, "收藏": 20, "评论": 5}, 单日上限=20)
    assert out["拒绝"] is False
