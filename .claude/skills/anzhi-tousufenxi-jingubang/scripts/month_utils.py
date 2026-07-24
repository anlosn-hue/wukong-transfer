# -*- coding: utf-8 -*-
"""月份算术共用工具：YYYY-MM 字符串按日历精确偏移。
m01/m02/m06/m07 统一用此函数定位"上月"/"连续N月"，避免"排序后取相邻可用月"在数据缺月时
静默把缺口两边的月份当成相邻月（2026-07-07 代码审查+用户确认修复）。"""

def month_shift(month, delta):
    y, m = int(month[:4]), int(month[5:7])
    m += delta
    y, m = y + (m - 1) // 12, (m - 1) % 12 + 1
    return f"{y}-{m:02d}"
