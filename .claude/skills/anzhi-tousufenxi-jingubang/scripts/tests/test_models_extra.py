# -*- coding: utf-8 -*-
import pandas as pd
from test_models_core import _ctx
from models import m05_concentration, m06_newcomers, m07_repeaters

def test_m05_top5_share(lib_two_months):
    r = m05_concentration.run(_ctx(lib_two_months), {"启用": True})
    assert r["指标"]["Top5占比"] == "100.0%"  # 夹具单一问题点

def test_m06_newcomer_yellow(lib_two_months):
    p = lib_two_months / "底库" / "tousu" / "2026-06.csv"
    df = pd.read_csv(p, encoding="utf-8-sig")
    extra = df.iloc[[0] * 4].copy()
    extra[["二级菜单", "三级菜单", "问题点"]] = ["新业务", "新故障", "新业务-新故障"]
    pd.concat([df, extra]).to_csv(p, index=False, encoding="utf-8-sig")
    r = m06_newcomers.run(_ctx(lib_two_months), {"启用": True, "门槛": 3})
    ws = [w for w in r["预警"] if w["问题点"] == "新业务-新故障"]
    assert ws and ws[0]["级别"] == "黄" and "上月0笔" in ws[0]["依据"]

def test_m06_no_warning_when_prev_month_is_a_gap(lib_two_months):
    # 代码审查发现：此前用"排序后取相邻可用月"，若7月缺失，8月运行会把6月错当成"上月"
    tousu_dir = lib_two_months / "底库" / "tousu"
    pd.read_csv(tousu_dir / "2026-06.csv", encoding="utf-8-sig").to_csv(
        tousu_dir / "2026-08.csv", index=False, encoding="utf-8-sig")
    ctx = _ctx(lib_two_months, month="2026-08")
    r = m06_newcomers.run(ctx, {"启用": True, "门槛": 3})
    assert r["指标"]["投诉"] == "无上月数据，跳过"

def test_m07_repeater_needs_streak(lib_two_months):
    r = m07_repeaters.run(_ctx(lib_two_months), {"启用": True, "连续月数": 3})
    assert r["指标"]["惯犯"] == []  # 只有2个月数据，凑不满3连
    assert r["预警"] == []  # 惯犯模型设计上不出预警条目（代码审查发现此前无断言锁定该不变量）
    r2 = m07_repeaters.run(_ctx(lib_two_months), {"启用": True, "连续月数": 2})
    assert "协商还款问题-逾期无力归还" in [x["问题点"] for x in r2["指标"]["惯犯"]]
    assert r2["预警"] == []

def test_m07_no_streak_when_middle_month_missing(lib_two_months):
    # 代码审查发现：5/6/8三月都有数据，但7月缺失时不应被算作"连续3个月"
    tousu_dir = lib_two_months / "底库" / "tousu"
    pd.read_csv(tousu_dir / "2026-06.csv", encoding="utf-8-sig").to_csv(
        tousu_dir / "2026-08.csv", index=False, encoding="utf-8-sig")
    ctx = _ctx(lib_two_months, month="2026-08")
    r = m07_repeaters.run(ctx, {"启用": True, "连续月数": 3})
    assert r["指标"]["惯犯"] == []

from models import m08_activity

INDEX_MD = """# 活动方案库 · 全景清单

| 活动ID | 活动名 | 来源 | 类型 | 客群 | 时间窗 | 渠道 | 状态 | 风险等级 | 舆情关键词 | 下次盯盘节点 | 评估校正 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20260601-x-测试活动 | 测试抽奖活动 | internal | 活动 | 用户 | 2026-06-01~2026-07-31 | APP | 进行中 | 三级 | 投诉内容样例,抽不中 | - | - |
| 20260101-x-已结束活动 | 早已结束 | internal | 活动 | 用户 | 2026-01-01~2026-02-01 | APP | 已结束 | 四级 | 不会命中词 | - | - |
| 20260610-x-待填活动 | 时间待填 | internal | 系统维护 | 用户 | 待填~待填 | APP | 进行中 | 三级 | 系统维护 | - | - |
"""

def test_m08_matches_inflight_and_skips_ended(lib_two_months, tmp_path):
    idx = tmp_path / "INDEX.md"
    idx.write_text(INDEX_MD, encoding="utf-8")
    ctx = _ctx(lib_two_months); ctx["activity_index"] = str(idx)
    r = m08_activity.run(ctx, {"启用": True})
    hits = {a["活动名"]: a for a in r["指标"]["活动"]}
    assert "测试抽奖活动" in hits          # 时间窗覆盖6月
    assert "早已结束" not in hits          # 1-2月活动不入当月分析
    assert "时间待填" in hits              # 待填但状态=进行中 → 纳入
    assert hits["测试抽奖活动"]["投诉命中"] >= 1  # 夹具反馈内容含"投诉内容样例"
    assert hits["测试抽奖活动"]["命中关键词"]["投诉内容样例"] >= 1

def test_m08_empty_state(lib_two_months):
    ctx = _ctx(lib_two_months); ctx["activity_index"] = "Z:/不存在/INDEX.md"
    r = m08_activity.run(ctx, {"启用": True})
    assert "本月无在途活动/变更" in r["md"]

def test_m08_missing_activity_index_key_no_crash(lib_two_months):
    # 代码审查发现的Critical：ctx里键缺失/None时 Path("")解析成当前目录，read_text()会崩溃
    ctx = _ctx(lib_two_months)  # activity_index 键根本不存在
    r = m08_activity.run(ctx, {"启用": True})
    assert "本月无在途活动/变更" in r["md"]
    ctx["activity_index"] = None  # 显式None同理
    r2 = m08_activity.run(ctx, {"启用": True})
    assert "本月无在途活动/变更" in r2["md"]

def test_m08_end_date_only_excludes_after_expiry(lib_two_months, tmp_path):
    # 代码审查发现：起始待填、仅知结束日期的活动，一旦状态忘改回"已结束"，此前会无限期被判定在途
    idx_md = INDEX_MD + (
        "| 20260601-y-仅知结束日期 | 结束日期已知 | internal | 活动 | 用户 | "
        "待填~2026-06-30 | APP | 进行中 | 三级 | 结束日期测试词 | - | - |\n")
    idx = tmp_path / "INDEX.md"
    idx.write_text(idx_md, encoding="utf-8")
    ctx = _ctx(lib_two_months, month="2026-07")  # 已过6月30日的结束日期
    ctx["activity_index"] = str(idx)
    r = m08_activity.run(ctx, {"启用": True})
    hits = {a["活动名"]: a for a in r["指标"]["活动"]}
    assert "结束日期已知" not in hits  # 状态仍是"进行中"，但已过结束日期，应排除
