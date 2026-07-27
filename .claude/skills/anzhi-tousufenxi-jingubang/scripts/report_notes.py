# -*- coding: utf-8 -*-
"""报告首章「报告说明」+ 全文脚注文案的唯一事实源。

正文里凡出现需要解释的规则术语，写标记 〔fn:KEY〕；docx 渲染成页底真脚注，
md/html 渲染成文末注释。KEY 与本章表格同源，都由 指标.json 的参数快照推导，
下个月阈值一改，说明与脚注跟着变，不会说一套算一套。
"""
import re

from models import REGISTRY

MODEL_DISPLAY = {"惯犯": "重复问题"}
MODEL_DESC = {
    "排名分析": ("按诉点统计笔数与占比，出本月／今年／全量三个时间窗的 Top 榜，"
                 "并附意见来源分布与日趋势", "督办、投诉", "黄（首次进榜）"),
    "环比同比": ("同一诉点与上月、去年同月比较笔数变动", "督办、投诉", "橙（正向超标）"),
    "超时分析": ("统计督办工单超时办结情况，先全行后分部门", "督办", "橙（部门超标）"),
    "督办投诉比照": ("取投诉与督办两张表的重合部分：投诉侧已实际多发的诉点，"
                     "当月又出现在督办清单里，列为潜在投诉风险点", "督办×投诉", "红"),
    "集中度": ("Top5 诉点合计占当月投诉总量的比重，判断是点状集中还是面上分散",
               "投诉", "不出预警"),
    "新面孔": ("上月为零、本月冒出的诉点", "督办、投诉", "黄"),
    "惯犯": ("连续多月稳定进入 Top 榜的投诉诉点，作为写入声誉风险事件库的候选池",
             "投诉", "不出预警（升格候选）"),
    "活动关联": ("用活动方案库里在途活动的舆情关键词，在当月两表反馈文本中检索关联投诉",
                 "督办、投诉", "不出预警"),
}


def glossary(metrics):
    """正文术语悬浮表：[(术语, 释义)]，按术语长度降序（先长后短，避免短词抢先匹配）。

    释义直接取自本模块——报告说明章（二）用的是同一份 MODEL_DESC 与 footnotes()，
    所以悬浮里看到的和首章表格里写的必然一致，不会各说各的。
    """
    fn = footnotes(metrics)
    items = [("红色预警", fn["红警"]),
             ("橙色预警", fn["橙警环比"] + fn["橙警超时"]),
             ("黄色预警", fn["黄警"])]
    for name, (desc, tables, level) in MODEL_DESC.items():
        items.append((MODEL_DISPLAY.get(name, name),
                      "%s（分析模型）：%s。适用：%s；预警级别：%s。"
                      % (MODEL_DISPLAY.get(name, name), desc, tables, level)))
    return sorted(items, key=lambda kv: -len(kv[0]))


def term(label=None):
    """诉点／问题的分侧称谓（规范 A5，用户 2026-07-25 定）。

    投诉侧称「诉点」（＝投诉点），督办侧对应位置称「问题」。自造的「问题点」全库废止。
    底库列名仍叫「问题点」（schema 不动），本函数只管对客展示。"""
    return "问题" if str(label).strip() == "督办" else "诉点"


def period_label(month):
    """把底库月份标签渲染成中文期间名。支持后续按季度／半年／年度出报告。"""
    m = str(month).strip()
    for pat, fmt in ((r"^(\d{4})-(\d{1,2})$", lambda g: f"{g[0]}年{int(g[1])}月"),
                     (r"^(\d{4})-?Q([1-4])$", lambda g: f"{g[0]}年第{'一二三四'[int(g[1])-1]}季度"),
                     (r"^(\d{4})-?H([12])$", lambda g: f"{g[0]}年{'上下'[int(g[1])-1]}半年"),
                     (r"^(\d{4})$", lambda g: f"{g[0]}年度")):
        mo = re.match(pat, m)
        if mo:
            return fmt(mo.groups())
    return m


def _p(metrics, model, key, default):
    return metrics.get("参数快照", {}).get("分析模型", {}).get(model, {}).get(key, default)


def _dig(metrics, key, default):
    return metrics.get("参数快照", {}).get("深挖", {}).get(key, default)


def warn_rules(metrics):
    """预警认定规则（级别／模型／判定标准／适用表），供本章表格与脚注共用。"""
    mom_thr, mom_abs = _p(metrics, "环比同比", "阈值", 0.20), _p(metrics, "环比同比", "绝对增量门槛", 5)
    ot_thr = _p(metrics, "超时分析", "超时率阈值", 0.10)
    look = _p(metrics, "督办投诉比照", "回看月数", 3)
    avg = _p(metrics, "督办投诉比照", "月均笔数", 20)
    hit = _p(metrics, "督办投诉比照", "命中门槛", 10)
    new_thr = _p(metrics, "新面孔", "门槛", 3)
    topn = _p(metrics, "排名分析", "TopN", 10)
    return [
        ("红", "督办投诉比照",
         f"近{look}个月投诉单月均≥{avg}笔的多发诉点，当月督办单命中≥{hit}笔",
         "督办×投诉"),
        ("橙", "环比同比",
         f"同一诉点较上月变幅≥{mom_thr*100:.0f}%且增量≥{mom_abs}笔，两个条件同时满足；"
         f"只有上升才预警，下降同标准仅在报告中提示", "督办、投诉"),
        ("橙", "超时分析", f"该部门督办超时办结率≥{ot_thr*100:.0f}%", "督办"),
        ("黄", "新面孔", f"上月为零、本月新出现且≥{new_thr}笔的诉点", "督办、投诉"),
        # 措辞必须写明基准是「较上月」——实现是 m01_ranking 用 month_shift(-1) 与日历上月的
        # Top 榜比对。排名表「变动」列的"新进榜"另有基准（今年榜），两者不可混用同一个"首次"。
        ("黄", "排名分析", f"较上月新进入 Top{topn} 榜单的诉点", "督办、投诉"),
    ]


def footnotes(metrics):
    """全文脚注文案表：KEY → 脚注全文。"""
    rules = {r[1] + "|" + r[0]: r[2] for r in warn_rules(metrics)}
    ot_thr = _p(metrics, "超时分析", "超时率阈值", 0.10)
    # 兼容旧参数快照：2026-07-25 前的 指标.json 里键名还是「单问题点抽样上限条数」
    sample = _dig(metrics, "单诉点抽样上限条数", None) or _dig(metrics, "单问题点抽样上限条数", 150)
    levels = "／".join(_dig(metrics, "深挖预警级别", ["红", "橙"]))
    return {
        "督办": "督办：客户诉求已受理登记、尚未形成正式投诉的事前预警工单，须在时限内办结；"
                "与「投诉」是两张独立的数据表，不是同一批件的两个阶段。",
        "投诉": "投诉：已经形成的正式客户投诉，含 95561 电话、12378 引导、金融消保服务平台、"
                "金融监管总局等各来源渠道。",
        "红警": "红色预警：" + rules["督办投诉比照|红"] +
                "。含义是这个诉点在投诉侧已经实际发生且多发，同一诉点当月又出现在督办清单里，"
                "两张表在此重合即视为潜在的投诉风险点；不代表客户已向监管部门反映。",
        "橙警环比": "橙色预警（环比）：" + rules["环比同比|橙"] + "。",
        "橙警超时": "橙色预警（超时）：" + rules["超时分析|橙"] + "。",
        "黄警": "黄色预警：" + rules["新面孔|黄"] + "；以及" + rules["排名分析|黄"] + "。",
        "超时口径": f"超时办结率＝超时笔数÷当期总督办单量；超时笔数按「超时天数」字段为 1 天"
                    f"及以上的笔数统计。部门超时办结率≥{ot_thr*100:.0f}% 触发橙色预警。",
        # 内部层级代号 L1/L2/L3 不进交付件（规范 A1），但抽样规则必须留下——
        # 否则读者无从判断"深挖显示"覆盖了多少条（2026-06 报告即因此被处室打问号）。
        "深挖": f"深挖：对{levels}色预警命中的诉点，逐条精读客户反馈与处理结果原文，"
                f"归纳出子问题构成与成因；条数在 {sample} 条以内的全量精读，"
                f"超过 {sample} 条的随机抽样 {sample} 条（固定随机种子，同一批次可复现）。",
        "问题点": "诉点：由业务细分二级菜单与三级菜单拼成（三级为空时只取二级），"
                  "层级之间用「-」连接；菜单名本身含有的斜杠不是层级分隔符。"
                  "督办侧对应位置称「问题」。",
    }


def _table(head, rows):
    sep = "|" + "---|" * len(head)
    body = "\n".join("| " + " | ".join(str(c) for c in r) + " |" for r in rows)
    return "| " + " | ".join(head) + " |\n" + sep + "\n" + body


def build_intro(metrics):
    """首章「报告说明」章节体（结构与 report_outline 的其它章节一致）。"""
    scope = metrics.get("数据范围", {})
    badge = {"红": "🔴红", "橙": "🟠橙", "黄": "🟡黄"}

    # 本章只保留读者用得上的口径，不解释报告自身的做法（规范 B1）：
    # 原「（四）分析层级说明」整节删除（内部 L1/L2/L3 代号属 A1 禁列），
    # 原「（三）分析模型清单」并入（二）（用户 2026-07-25 定，规范 B1a）。
    parts = ["### （一）数据范围与部门口径"]
    rows = []
    for label, desc in (("督办", "客户来电沟通中未命中投诉关键词、已受理登记、"
                                 "尚未形成正式投诉单的事前预警工单"),
                        ("投诉", "客户来电沟通中已命中投诉关键词并形成的正式投诉单")):
        s = scope.get(label, {})
        rows.append([label, desc, f"{s.get('条数', '-')} 条", "、".join(s.get("机构", [])) or "-"])
    parts.append(_table(["数据表", "口径", "本期条数", "涉及部门"], rows))
    parts.append("数据来源为客服全渠道。部门取自本期数据实际出现的主办机构（督办侧）"
                 "与责任机构（投诉侧）。报告中的「诉点」〔fn:问题点〕是问题分类的最小单位。")
    # 跨表菜单归一必须披露：读者按诉点名回源表查时，得知道哪些名字被统一过（规范 A8a）
    menu_norm = metrics.get("菜单归一") or []
    if menu_norm:
        parts.append("两张表对同一业务的二级菜单命名存在差异，本期已按下列对应关系统一，"
                     "以保证跨表比照有效：" + "；".join(menu_norm) + "。")

    parts.append("### （二）预警级别认定规则与分析模型")
    parts.append("预警由模型按固定阈值自动判定，不含人工调整。同一诉点可能被多个模型同时命中，"
                 "预警总览按级别由高到低排列。红色预警需要两张表联合判定，只落在督办侧；"
                 "超时类橙色预警只有督办表有超时字段，投诉表不适用；集中度只看投诉表；"
                 "环比与新面孔两张表用同一套标准分别判定，互不合并。")
    parts.append(_table(["级别", "来源模型", "判定标准", "适用表"],
                        [[badge[lv], mdl, std, tbl] for lv, mdl, std, tbl in warn_rules(metrics)]))
    enabled = metrics.get("参数快照", {}).get("分析模型", {})
    mrows = []
    for name in REGISTRY:
        cfg = enabled.get(name, {})
        if not cfg.get("启用", False):
            continue
        desc, tbl, warn = MODEL_DESC.get(name, ("-", "-", "-"))
        fmt = lambda v: "／".join(str(x) for x in v) if isinstance(v, list) else str(v)
        params = "；".join(f"{k}={fmt(v)}" for k, v in cfg.items() if k != "启用") or "无"
        mrows.append([MODEL_DISPLAY.get(name, name), desc, tbl, warn, params])
    parts.append(_table(["模型", "作用", "适用表", "产出预警", "关键参数"], mrows))
    parts.append("标注「深挖显示」的结论来自对预警诉点的原文精读〔fn:深挖〕。")

    return {"title": "报告说明", "narrative": "", "insight": None, "risk": None,
            "table_md": "\n\n".join(parts), "chart": None, "note": None}
