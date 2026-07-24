# -*- coding: utf-8 -*-
"""A 层确定性筛选：风险语气词命中 或 互动数超阈值 → 命中候选；再经时间窗兜底过滤。
时间窗为降级兜底：可解析发布时间且落在窗外 → 滤除；解析不到日期 → 保留（不误杀）。"""
import re
from datetime import date, timedelta
from typing import List, Dict, Optional
from contract import Note

def 解析日期(raw: str, 今日: date) -> Optional[date]:
    """把小红书发布时间字符串尽力解析成 date；解析不到返回 None。
    支持：'2026-07-10' / '07-10' / 'N天前' / '昨天' / '今天'。其余一律 None。"""
    s = (raw or "").strip()
    if not s:
        return None
    if s in ("今天", "刚刚"):
        return 今日
    if s == "昨天":
        return 今日 - timedelta(days=1)
    m = re.match(r"(\d+)\s*天前", s)
    if m:
        return 今日 - timedelta(days=int(m.group(1)))
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.match(r"^(\d{1,2})-(\d{1,2})$", s)      # 无年份，按今年
    if m:
        return date(今日.year, int(m.group(1)), int(m.group(2)))
    return None

def 筛选A层(notes: List[Note], *, 风险语气词: List[str], 互动阈值: Dict[str, int],
          时间窗天数: int = None, 今日: date = None) -> List[Note]:
    今日 = 今日 or date.today()
    截止 = (今日 - timedelta(days=时间窗天数)) if 时间窗天数 else None
    for n in notes:
        原因 = []
        for w in 风险语气词:
            if w in n.标题:
                原因.append(f"风险词:{w}")
        高互动 = []
        if n.点赞 >= 互动阈值["点赞"]:
            高互动.append("点赞")
        if n.收藏 >= 互动阈值["收藏"]:
            高互动.append("收藏")
        if n.评论 >= 互动阈值["评论"]:
            高互动.append("评论")
        if 高互动:
            原因.append("互动超阈:" + "/".join(高互动))
        命中 = bool(原因)
        # 时间窗兜底：可解析出发布日期且早于截止 → 滤除；解析不到 → 保留
        if 命中 and 截止 is not None:
            d = 解析日期(n.发布时间, 今日)
            if d is not None and d < 截止:
                命中 = False
                原因 = [f"时间窗外({n.发布时间})"]
        n.筛选原因 = 原因
        n.命中筛选 = 命中
    return notes
