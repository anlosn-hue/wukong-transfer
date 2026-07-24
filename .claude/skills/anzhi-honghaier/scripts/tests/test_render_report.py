# -*- coding: utf-8 -*-
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from contract import Note, notes_to_json
import render_report

def _setup(d):
    p = Path(d); p.mkdir(parents=True, exist_ok=True)
    notes = [Note(id="n1", 标题="理财未到账", 作者="小明", 发布时间="2026-07-10",
                  点赞=120, 收藏=30, 评论=8, 链接="https://x/n1",
                  命中筛选=True, 筛选原因=["风险词:未到账"])]
    (p/"清单.json").write_text(json.dumps({"查询":{"关键词":"理财","时间窗天数":30,"通道":"playwright"},
        **notes_to_json(notes)}, ensure_ascii=False), encoding="utf-8")
    (p/"研判.json").write_text(json.dumps({"研判":[{"id":"n1","情绪":"负面","涉我行":True,
        "风险性质":"疑似真实投诉","高风险":True,"摘录":"做完任务立减金没到账","研判说明":"多次提及未到账"}]},
        ensure_ascii=False), encoding="utf-8")
    (p/"发酵.json").write_text(json.dumps({"发酵":[{"id":"n1","群体信号":True,
        "复现表述":["我也没到账","+1"],"发酵度":"高","说明":"评论区多人同诉"}]},
        ensure_ascii=False), encoding="utf-8")

def test_render_report(tmp_path):
    _setup(str(tmp_path))
    render_report.执行(输出目录=str(tmp_path))
    md = (tmp_path/"报告.md").read_text(encoding="utf-8")
    assert "理财" in md and "疑似真实投诉" in md
    assert "https://x/n1" in md          # 链接可点回原帖
    assert "发酵度：高" in md or "高" in md

def test_render_report_no_research(tmp_path):
    # 只有清单（跑到 A 就停），研判/发酵缺失也能出报告
    p = Path(tmp_path); p.mkdir(parents=True, exist_ok=True)
    (p/"清单.json").write_text(json.dumps({"查询":{"关键词":"理财","时间窗天数":30,"通道":"playwright"},
        "笔记":[]}, ensure_ascii=False), encoding="utf-8")
    render_report.执行(输出目录=str(tmp_path))
    md = (tmp_path/"报告.md").read_text(encoding="utf-8")
    assert "无命中" in md
