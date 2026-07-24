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
    "排名分析": ("按问题点统计笔数与占比，出本月／今年／全量三个时间窗的 Top 榜，"
                 "并附意见来源分布与日趋势", "督办、投诉", "黄（首次进榜）"),
    "环比同比": ("同一问题点与上月、去年同月比较笔数变动", "督办、投诉", "橙（正向超标）"),
    "超时分析": ("统计督办工单超时办结情况，先全行后分部门", "督办", "橙（部门超标）"),
    "督办投诉比照": ("把投诉侧多发问题点与当月督办清单比对，找出仍停留在督办环节、"
                     "有转为正式投诉压力的诉求", "督办×投诉", "红"),
    "集中度": ("Top5 问题点合计占当月投诉总量的比重，判断是点状集中还是面上分散",
               "投诉", "不出预警"),
    "新面孔": ("上月为零、本月冒出的问题点", "督办、投诉", "黄"),
    "惯犯": ("连续多月稳定进入 Top 榜的投诉问题点，作为写入声誉风险事件库的候选池",
             "投诉", "不出预警（升格候选）"),
    "活动关联": ("用活动方案库里在途活动的舆情关键词，在当月两表反馈文本中检索关联投诉",
                 "督办、投诉", "不出预警"),
}


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
         f"投诉侧近{look}个月月均≥{avg}笔的多发问题点，当月督办命中≥{hit}笔",
         "督办×投诉"),
        ("橙", "环比同比",
         f"同一问题点较上月变幅≥{mom_thr*100:.0f}%且增量≥{mom_abs}笔，两个条件同时满足；"
         f"只有上升才预警，下降同标准仅在报告中提示", "督办、投诉"),
        ("橙", "超时分析", f"该部门督办超时办结率≥{ot_thr*100:.0f}%", "督办"),
        ("黄", "新面孔", f"上月为零、本月新出现且≥{new_thr}笔的问题点", "督办、投诉"),
        ("黄", "排名分析", f"本月首次进入 Top{topn} 榜单的问题点", "督办、投诉"),
    ]


def footnotes(metrics):
    """全文脚注文案表：KEY → 脚注全文。"""
    rules = {r[1] + "|" + r[0]: r[2] for r in warn_rules(metrics)}
    ot_thr = _p(metrics, "超时分析", "超时率阈值", 0.10)
    sample = _dig(metrics, "单问题点抽样上限条数", 150)
    levels = "／".join(_dig(metrics, "深挖预警级别", ["红", "橙"]))
    return {
        "督办": "督办：客户诉求已受理登记、尚未形成正式投诉的事前预警工单，须在时限内办结；"
                "与「投诉」是两张独立的数据表，不是同一批件的两个阶段。",
        "投诉": "投诉：已经形成的正式客户投诉，含 95561 电话、12378 引导、金融消保服务平台、"
                "金融监管总局等各来源渠道。",
        "红警": "红色预警：" + rules["督办投诉比照|红"] +
                "。含义是这个问题点在投诉侧已经多发，当月又有相当数量的诉求停留在督办环节，"
                "存在继续转化为正式投诉的压力；不代表客户已向监管部门反映。",
        "橙警环比": "橙色预警（环比）：" + rules["环比同比|橙"] + "。",
        "橙警超时": "橙色预警（超时）：" + rules["超时分析|橙"] + "。",
        "黄警": "黄色预警：" + rules["新面孔|黄"] + "；以及" + rules["排名分析|黄"] + "。",
        "超时口径": f"超时办结率＝超时笔数÷当期总督办单量；超时笔数按「超时天数」字段为 1 天"
                    f"及以上的笔数统计。部门超时办结率≥{ot_thr*100:.0f}% 触发橙色预警。",
        "深挖": f"L2 分批深挖：对{levels}色预警命中的问题点，逐条精读客户反馈与处理结果原文，"
                f"归纳出子问题构成与成因；单个问题点超过 {sample} 条时随机抽样 {sample} 条"
                f"（固定随机种子，同一批次可复现），其余不再逐条读。",
        "问题点": "问题点：由业务细分二级菜单与三级菜单拼成（三级为空时只取二级），"
                  "层级之间用「-」连接；菜单名本身含有的斜杠不是层级分隔符。",
    }


def _table(head, rows):
    sep = "|" + "---|" * len(head)
    body = "\n".join("| " + " | ".join(str(c) for c in r) + " |" for r in rows)
    return "| " + " | ".join(head) + " |\n" + sep + "\n" + body


def build_intro(metrics):
    """首章「报告说明」章节体（结构与 report_outline 的其它章节一致）。"""
    scope = metrics.get("数据范围", {})
    期间 = period_label(metrics.get("月份", ""))
    badge = {"红": "🔴红", "橙": "🟠橙", "黄": "🟡黄"}

    parts = ["### （一）数据范围与部门口径",
             f"本报告分析{期间}的客户督办与客户投诉两张数据表。两张表口径不同，"
             f"各自独立统计，报告中所有指标都注明取自哪张表。"]
    rows = []
    for label, desc in (("督办", "客户诉求已受理登记、尚未形成正式投诉的事前预警工单，须限时办结"),
                        ("投诉", "已经形成的正式客户投诉")):
        s = scope.get(label, {})
        rows.append([label, desc, f"{s.get('条数', '-')} 条", "、".join(s.get("机构", [])) or "-"])
    parts.append(_table(["数据表", "口径", "本期条数", "涉及部门"], rows))
    parts.append("部门清单取自本期数据实际出现的主办机构（督办侧）与责任机构（投诉侧），"
                 "与原始数据《说明》页列明的五个部门口径一致；投诉侧责任机构按原始数据的"
                 "合并称谓原样保留。报告中的「问题点」〔fn:问题点〕是问题分类的最小单位。")

    parts.append("### （二）预警级别认定规则")
    parts.append("预警由模型按固定阈值自动判定，不含人工调整。同一问题点可能被多个模型同时命中，"
                 "预警总览按级别由高到低排列。")
    parts.append(_table(["级别", "来源模型", "判定标准", "适用表"],
                        [[badge[lv], mdl, std, tbl] for lv, mdl, std, tbl in warn_rules(metrics)]))
    parts.append("督办与投诉的预警规则存在差异：红色预警需要两张表联合判定，只落在督办侧；"
                 "超时类橙色预警只有督办表有超时字段，投诉表不适用；集中度只看投诉表；"
                 "环比与新面孔两张表用同一套标准分别判定，互不合并。")

    parts.append("### （三）分析模型清单")
    parts.append("本期启用的模型如下，各章节的数据均由对应模型产出。")
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

    parts.append("### （四）分析层级说明")
    parts.append("同一份数据分三个层级看，层级越深读得越细、覆盖面越窄。")
    sample = _dig(metrics, "单问题点抽样上限条数", 150)
    levels = "／".join(_dig(metrics, "深挖预警级别", ["红", "橙"]))
    parts.append(_table(["层级", "名称", "做法", "覆盖范围"], [
        ["L1", "定量扫描", "各模型对当期全量数据做机器统计，产出排名、变动、超时、预警等指标",
         "当期全部数据，逐条计入"],
        ["L2", "分批深挖", "对预警命中的问题点，逐条精读客户反馈与处理结果原文，归纳子问题与成因",
         f"{levels}色预警问题点；单个问题点超 {sample} 条时随机抽样 {sample} 条"],
        ["L3", "专题深挖", "针对单个问题点跨月拉通分析，看趋势演变与处理质量", "手动触发，不随月报自动执行"],
    ]))
    parts.append("本报告的定量章节均为 L1 结果；标注「深挖显示」的结论来自 L2〔fn:深挖〕。")

    return {"title": "报告说明", "narrative": "", "insight": None, "risk": None,
            "table_md": "\n\n".join(parts), "chart": None, "note": None}
