# -*- coding: utf-8 -*-
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ledger import record_query, count_today, cap_ok, 会话抓取数

def test_cap_counts_only_A_layer(tmp_path):
    lp = tmp_path / "台账.jsonl"
    # 一次完整查询 = A/B/C 各一条；单日上限只认 A 层，不被 B/C 撑爆
    for _ in range(3):
        record_query(str(lp), 关键词="理财", 通道="playwright", 层级="A", 抓取量=1)
        record_query(str(lp), 关键词="理财", 通道="playwright", 层级="B", 抓取量=5)
        record_query(str(lp), 关键词="理财", 通道="playwright", 层级="C", 抓取量=2)
    assert count_today(str(lp)) == 9              # 全部条目
    assert count_today(str(lp), 层级="A") == 3    # 只数 A 层
    assert cap_ok(str(lp), 单日上限=3, 层级="A") is False   # 3 次查询已达上限
    assert cap_ok(str(lp), 单日上限=5, 层级="A") is True

def test_record_shape(tmp_path):
    lp = tmp_path / "台账.jsonl"
    record_query(str(lp), 关键词="理财", 通道="playwright", 层级="B", 抓取量=7)
    line = json.loads(lp.read_text(encoding="utf-8").strip())
    assert line["关键词"] == "理财" and line["抓取量"] == 7 and "时间" in line

def test_会话抓取数(tmp_path):
    d = tmp_path / "20260711-理财"
    (d / "正文").mkdir(parents=True); (d / "评论").mkdir()
    (d / "清单.json").write_text("{}", encoding="utf-8")
    (d / "正文" / "n1.txt").write_text("x", encoding="utf-8")
    (d / "正文" / "n2.txt").write_text("x", encoding="utf-8")
    (d / "评论" / "n1.txt").write_text("x", encoding="utf-8")
    assert 会话抓取数(str(d)) == 4    # 1 次搜索 + 2 正文 + 1 评论
