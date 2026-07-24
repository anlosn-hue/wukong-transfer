# -*- coding: utf-8 -*-
import pandas as pd
import run_analysis
from models import m01_ranking

def _ctx(base, month="2026-06"):
    data = run_analysis.load_lib(base / "底库")
    return {"month": month, "duban": data["duban"], "tousu": data["tousu"],
            "config": {}, "activity_index": None}

def test_m01_three_windows_and_new_entry(lib_two_months):
    ctx = _ctx(lib_two_months)
    r = m01_ranking.run(ctx, {"启用": True, "TopN": 10, "时间窗": ["本月", "今年", "全量"]})
    idx = r["指标"]
    assert "本月" in idx["督办"] and "今年" in idx["督办"] and "全量" in idx["督办"]
    top1 = idx["投诉"]["本月"][0]
    assert top1["问题点"] == "协商还款问题-逾期无力归还" and top1["笔数"] == 12
    assert top1["占比"] == "100.0%"
    # 本月明细（此前代码审查发现的覆盖率缺口）：意见来源分布 + 日趋势
    detail = idx["投诉"]["本月明细"]["协商还款问题-逾期无力归还"]
    assert detail["意见来源"] == {"95561电话": 12}  # 夹具全部同一来源
    assert sum(detail["日趋势"].values()) == 12 and detail["日趋势"]["01"] == 2
    # 夹具两月问题点相同 → 无"首进榜"黄警
    assert r["预警"] == []
    assert "本月" in r["md"]

def test_m01_new_entry_yellow(lib_two_months):
    # 6月新增一个5月没有的问题点 → 黄警
    df = pd.read_csv(lib_two_months / "底库" / "tousu" / "2026-06.csv", encoding="utf-8-sig")
    extra = df.iloc[[0] * 3].copy()
    extra[["二级菜单", "三级菜单", "问题点"]] = ["新业务", "新故障", "新业务-新故障"]
    pd.concat([df, extra]).to_csv(lib_two_months / "底库" / "tousu" / "2026-06.csv",
                                  index=False, encoding="utf-8-sig")
    ctx = _ctx(lib_two_months)
    r = m01_ranking.run(ctx, {"启用": True, "TopN": 10, "时间窗": ["本月"]})
    hits = [w for w in r["预警"] if w["问题点"] == "新业务-新故障"]
    assert hits and hits[0]["级别"] == "黄" and hits[0]["表"] == "投诉"

def test_m01_no_yellow_when_prev_month_is_a_gap(lib_two_months):
    # 代码审查发现：此前用"排序后取相邻可用月"，若7月缺失，8月运行会把6月错当成"上月"
    tousu_dir = lib_two_months / "底库" / "tousu"
    pd.read_csv(tousu_dir / "2026-06.csv", encoding="utf-8-sig").to_csv(
        tousu_dir / "2026-08.csv", index=False, encoding="utf-8-sig")  # 8月=6月同数据，7月缺失
    ctx = _ctx(lib_two_months, month="2026-08")
    r = m01_ranking.run(ctx, {"启用": True, "TopN": 10, "时间窗": ["本月"]})
    assert r["预警"] == []  # 7月缺失，不应把6月错当"上月"来判断首进榜

from models import m02_mom_yoy, m03_overtime

def test_m02_orange_needs_both_thresholds(lib_two_months):
    # 夹具：投诉同问题点 5月4笔→6月12笔 = +200% 且 +8笔 → 橙警
    ctx = _ctx(lib_two_months)
    r = m02_mom_yoy.run(ctx, {"启用": True, "阈值": 0.20, "绝对增量门槛": 5})
    oranges = [w for w in r["预警"] if w["级别"] == "橙" and w["表"] == "投诉"]
    assert len(oranges) == 1 and "+200.0%" in oranges[0]["依据"]
    # 督办 6→9 = +50% 但 +3笔 < 门槛5 → 不预警（双门槛防低基数）
    assert not [w for w in r["预警"] if w["表"] == "督办"]
    assert r["指标"]["投诉"]["同比"] == "无去年同月数据"

def test_m02_yoy_flag_independent_of_missing_prev(lib_two_months):
    # 代码审查发现的bug：上月缺失时"同比"曾被硬编码为"无去年同月数据"，即使去年同月数据其实存在
    yoy_month = "2025-05"
    df = pd.read_csv(lib_two_months / "底库" / "tousu" / "2026-05.csv", encoding="utf-8-sig")
    df.to_csv(lib_two_months / "底库" / "tousu" / f"{yoy_month}.csv", index=False, encoding="utf-8-sig")
    ctx = _ctx(lib_two_months, month="2026-05")
    r = m02_mom_yoy.run(ctx, {"启用": True, "阈值": 0.20, "绝对增量门槛": 5})
    assert r["指标"]["投诉"]["环比"] == "无上月数据"  # 2026-04 不存在
    assert r["指标"]["投诉"]["同比"] == "已启用"  # 2025-05 存在，不应被环比缺失覆盖

def test_m02_drop_noted_not_warned(lib_two_months, tmp_path):
    # 构造骤降：6月投诉砍到1笔
    p = lib_two_months / "底库" / "tousu" / "2026-06.csv"
    pd.read_csv(p, encoding="utf-8-sig").head(1).to_csv(p, index=False, encoding="utf-8-sig")
    r = m02_mom_yoy.run(_ctx(lib_two_months), {"启用": True, "阈值": 0.20, "绝对增量门槛": 5})
    assert r["预警"] == []  # 负向不进预警清单
    assert r["指标"]["投诉"]["骤降提示"]  # 但报告里有提示

def test_m03_overall_then_department(lib_two_months):
    # 改造督办6月：9笔中 3笔带超时天数（2笔4天、1笔30天）；
    # 其中1笔「是否超时办结」标志位是"否"——新口径只认天数，仍须计为超时（用户2026-07-21定）
    p = lib_two_months / "底库" / "duban" / "2026-06.csv"
    df = pd.read_csv(p, encoding="utf-8-sig")
    df.loc[0:1, ["是否超时办结", "超时状态", "超时天数"]] = ["否", "超时", 4.0]
    df.loc[2, ["是否超时办结", "超时状态", "超时天数"]] = ["", "超时", 30.0]
    df.to_csv(p, index=False, encoding="utf-8-sig")
    r = m03_overtime.run(_ctx(lib_two_months), {"启用": True, "超时率阈值": 0.10})
    assert r["指标"]["全行"]["超时笔数"] == 3 and r["指标"]["全行"]["超时办结率"] == "33.3%"
    dept = r["指标"]["部门"]["数字运营部"]
    assert dept["4-7天"] == 2 and dept["8天及以上"] == 1 and dept["1-3天"] == 0
    assert dept["超时天数最大"] == 30
    assert [w for w in r["预警"] if w["级别"] == "橙" and "数字运营部" in w["依据"]]
    # 超时Top5（此前代码审查发现的覆盖率缺口）：按超时天数降序，无天数的已被过滤
    top5 = r["指标"]["超时Top5"]
    assert len(top5) == 3  # 夹具仅3笔带超时天数
    assert top5[0]["超时天数"] == 30
    assert [t["超时天数"] for t in top5] == sorted((t["超时天数"] for t in top5), reverse=True)

from models import m04_escalation

def test_m04_red_on_escalation(lib_two_months):
    # 让督办6月出现投诉多发问题点：改3条督办为投诉侧的问题点
    p = lib_two_months / "底库" / "duban" / "2026-06.csv"
    df = pd.read_csv(p, encoding="utf-8-sig")
    df.loc[0:2, ["二级菜单", "三级菜单", "问题点"]] = ["协商还款问题", "逾期无力归还",
                                                       "协商还款问题-逾期无力归还"]
    df.to_csv(p, index=False, encoding="utf-8-sig")
    ctx = _ctx(lib_two_months)
    r = m04_escalation.run(ctx, {"启用": True, "回看月数": 3, "月均笔数": 5, "命中门槛": 3})
    reds = [w for w in r["预警"] if w["级别"] == "红"]
    assert len(reds) == 1
    assert reds[0]["问题点"] == "协商还款问题-逾期无力归还"
    assert "当月另有3笔" in reds[0]["依据"] and "转为正式投诉" in reds[0]["依据"]
    # 走势数据存在（供预警点文件渲染近3月走势）
    assert "走势" in r["指标"] and "协商还款问题-逾期无力归还" in r["指标"]["走势"]

def test_m04_below_threshold_no_red(lib_two_months):
    r = m04_escalation.run(_ctx(lib_two_months),
                           {"启用": True, "回看月数": 3, "月均笔数": 5, "命中门槛": 3})
    assert [w for w in r["预警"] if w["级别"] == "红"] == []  # 未改造时督办无命中

def test_m04_prolific_union_not_intersection(lib_two_months):
    # 代码审查发现的覆盖率缺口：多发集合是TopN"并集"月均阈值，而非"交集"，此前无测试真正区分过
    for month, n in [("2026-05", 7), ("2026-06", 7)]:
        p = lib_two_months / "底库" / "tousu" / f"{month}.csv"
        df = pd.read_csv(p, encoding="utf-8-sig")
        extra = df.iloc[[0] * n].copy()
        extra[["二级菜单", "三级菜单", "问题点"]] = ["网银登录问题", "验证码失效", "网银登录问题/验证码失效"]
        pd.concat([df, extra]).to_csv(p, index=False, encoding="utf-8-sig")
    ctx = _ctx(lib_two_months)
    ctx["config"] = {"分析模型": {"排名分析": {"TopN": 1}}}  # 强制TopN=1，制造"仅满足月均"的排他场景
    r = m04_escalation.run(ctx, {"启用": True, "回看月数": 3, "月均笔数": 5, "命中门槛": 3})
    # "协商还款问题-逾期无力归还"16笔排第一，唯一入选TopN=1；
    # "网银登录问题/验证码失效"14笔/2月=7≥5，排第二被TopN排除——若代码误用交集(&)会被漏掉，并集(|)才能入选
    assert "网银登录问题/验证码失效" in r["指标"]["多发类型"]
    assert len(r["指标"]["多发类型"]) == 2
