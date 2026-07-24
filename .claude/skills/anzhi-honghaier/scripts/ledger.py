# -*- coding: utf-8 -*-
"""查询台账 + 两级频率上限：
- 单日查询次数：只数 A 层台账条目（一次查询=一次 A 层搜索），B/C 抓取不算新查询。
- 单次会话抓取量：按查询目录里已落盘的抓取物计数（跨 A/B/C 三个独立进程共享状态）。"""
import json
from datetime import datetime, date
from pathlib import Path

def record_query(台账路径: str, *, 关键词: str, 通道: str, 层级: str, 抓取量: int):
    p = Path(台账路径)
    p.parent.mkdir(parents=True, exist_ok=True)
    entry = {"时间": datetime.now().isoformat(timespec="seconds"),
             "日期": date.today().isoformat(), "关键词": 关键词,
             "通道": 通道, "层级": 层级, "抓取量": 抓取量}
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def count_today(台账路径: str, *, 层级: str = None) -> int:
    """今日台账条目数；层级给定时只数该层。"""
    p = Path(台账路径)
    if not p.exists():
        return 0
    today = date.today().isoformat()
    n = 0
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        if rec.get("日期") != today:
            continue
        if 层级 is not None and rec.get("层级") != 层级:
            continue
        n += 1
    return n

def cap_ok(台账路径: str, *, 单日上限: int, 层级: str = "A") -> bool:
    """单日查询上限检查：默认只数 A 层（真实"发起查询"次数）。"""
    return count_today(台账路径, 层级=层级) < 单日上限

def 会话抓取数(输出目录: str) -> int:
    """单次查询已发生的抓取动作总数（1 次搜索 + 已抓正文数 + 已抓评论数），
    状态存在查询目录里，A/B/C 三个独立进程共享，做跨层会话上限的依据。"""
    d = Path(输出目录)
    搜索 = 1 if (d / "清单.json").exists() else 0
    正文 = len(list((d / "正文").glob("*.txt"))) if (d / "正文").exists() else 0
    评论 = len(list((d / "评论").glob("*.txt"))) if (d / "评论").exists() else 0
    return 搜索 + 正文 + 评论
