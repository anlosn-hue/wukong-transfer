# -*- coding: utf-8 -*-
"""渲染五件产出+INDEX。用法：python render_report.py <报告月份dir> <config.yaml>
读取 <dir>/指标.json + 可选 摘要.json；数据区/预警点路径取自 config。"""
import html as _html
import json, re as _re, sys
from datetime import datetime
from pathlib import Path
import yaml
import chart_images, base64, report_notes, report_outline
from marker_utils import TextFootnotes, strip_markers, strip_tips, sub_tips

BADGE = {"红": "🔴", "橙": "🟠", "黄": "🟡"}
MODEL_ORDER = ["超时分析", "排名分析", "环比同比", "督办投诉比照", "集中度", "新面孔", "活动关联", "惯犯"]
MODEL_DISPLAY = {"惯犯": "重复问题"}  # 报告文字用"重复问题"，配置key/内部模型名仍叫"惯犯"（升格候选池语义）

CSS = """body{font-family:'Microsoft YaHei',sans-serif;max-width:960px;margin:24px auto;
padding:0 16px;color:#222;line-height:1.7}h1{border-bottom:3px solid #b8202e;padding-bottom:8px}
h2{border-left:4px solid #b8202e;padding-left:8px;margin-top:32px}table{border-collapse:collapse;
width:100%;margin:12px 0;font-size:14px}th,td{border:1px solid #ccc;padding:6px 10px;text-align:left}
th{background:#f5f5f5}code{background:#f0f0f0;padding:1px 4px;border-radius:3px}
.badge红{color:#b8202e;font-weight:bold}.badge橙{color:#d97706;font-weight:bold}
.badge黄{color:#a16207;font-weight:bold}"""

def _escape_bold(t):
    """markdown **加粗** → <b>。落单的 ** 按字面留着：**不能**让它把加粗一路开到段尾，
    那会静默毁掉整段排版且很难查（数据里混进星号就会发生）。"""
    t = _html.escape(t)
    if t.count("**") % 2:
        return t
    while "**" in t:
        t = t.replace("**", "<b>", 1).replace("**", "</b>", 1)
    return t

def md_to_html(md):
    out, table, in_tbl, in_list = [], [], False, False
    def flush():
        nonlocal table, in_tbl
        if table:
            head, *body = [r for r in table if set(r.replace("|", "").strip()) - {"-", " ", ":"}]
            cells = lambda r: [c.strip() for c in r.strip().strip("|").split("|")]
            out.append("<table><tr>" + "".join(f"<th>{_html.escape(c)}</th>" for c in cells(head)) + "</tr>"
                       + "".join("<tr>" + "".join(f"<td>{_html.escape(c)}</td>" for c in cells(r)) + "</tr>"
                                 for r in body) + "</table>")
        table, in_tbl = [], False
    def close_list():
        nonlocal in_list
        if in_list:
            out.append("</ul>"); in_list = False
    for line in md.splitlines():
        s = line.strip()
        if s.startswith("|"):
            close_list()
            table.append(s); in_tbl = True; continue
        if in_tbl:
            flush()
        if s.startswith("- "):
            if not in_list:
                out.append("<ul>"); in_list = True
            out.append(f"<li>{_escape_bold(s[2:])}</li>")
            continue
        close_list()
        if s.startswith("###"):
            out.append(f"<h3>{_html.escape(s[3:].strip())}</h3>")
        elif s.startswith("##"):
            out.append(f"<h2>{_html.escape(s[2:].strip())}</h2>")
        elif s.startswith("#"):
            out.append(f"<h1>{_html.escape(s[1:].strip())}</h1>")
        elif s:
            out.append(f"<p>{_escape_bold(s)}</p>")
    flush()
    close_list()
    return "\n".join(out)

def build_md(metrics, summaries, narrative=None):
    m = metrics
    tf = TextFootnotes(report_notes.footnotes(m))
    # md 是工作底稿，同样没有悬停形态：悬浮标记退化为标签，明细在附件里
    mark = lambda t: strip_tips(tf.sub(t, lambda n, k: f"[^{n}]"))
    intro = report_notes.build_intro(m)
    lines = [f"# 客户投诉分析月报 · {report_notes.period_label(m['月份'])}",
             f"\n> 生成：{m['生成时间']} · 金箍棒（anzhi-tousufenxi-jingubang）",
             "\n## 报告说明\n", mark(intro["table_md"]),
             "\n## 参数快照\n", "```yaml",
             yaml.safe_dump(m["参数快照"], allow_unicode=True, sort_keys=False).strip(), "```",
             "\n## 预警总览\n", "| 级别 | 表 | 诉点／问题 | 依据 | 来源 |", "|---|---|---|---|---|"]
    for w in m["预警汇总"]:
        lines.append(f"| {BADGE[w['级别']]}{w['级别']} | {w['表']} | {w['问题点'] or '-'} | "
                     f"{w['依据']} | {w['来源模型']} |")
    if not m["预警汇总"]:
        lines.append("| - | - | 本月无预警 | - | - |")
    for name in MODEL_ORDER:
        if name in m["模型"]:
            lines += ["\n## " + MODEL_DISPLAY.get(name, name), "", m["模型"][name]["md"]]
    # 数据质量提示：只进 md 工作底稿，不进正式 docx——这是给舆情管理员自查的，不是给处室看的。
    # 「督办零命中」比「疑似命名错配」更宽：后者只认三级菜单相同的情形，三级菜单名也漂移时探不到。
    esc = m.get("模型", {}).get("督办投诉比照", {}).get("指标", {})
    mism, zero = esc.get("疑似命名错配") or [], esc.get("督办零命中") or []
    if mism or zero:
        lines.append("\n## 数据质量提示（内部自查，不随正式报告交付）\n")
        for x in mism:
            lines.append(f"- ⚠️ 疑似跨表命名错配：投诉侧「{x['投诉侧问题点']}」 ⇄ 督办侧 "
                         f"{'、'.join(x['督办侧疑似对应'])}（{x['督办侧笔数']}笔）"
                         f"，确认后补入 `底库/菜单映射.yaml`")
        if zero:
            lines.append(f"- 以下 {len(zero)} 个投诉多发诉点本月督办侧零命中，"
                         f"请人工确认是确无同类督办、还是两表命名不一致：")
            lines += [f"  - {p}" for p in zero]

    lines.append("\n## 归因摘要（原文精读）\n")  # 内部层级代号 L2 不进交付件（规范 A1）
    if summaries:
        for p, s in summaries.items():
            subs = "；".join(f"{x['主题']}×{x['条数']}（{x['典型例']}）" for x in s.get("子问题", []))
            lines += [f"### {p}", f"- **归因**：{s.get('归因','')}", f"- **子问题**：{subs}",
                      f"- **处理对症性**：{s.get('处理对症','')}",
                      f"- **空处理结果占比**：{s.get('空处理结果占比','-')}", ""]
    else:
        lines.append("（本月无红色、橙色预警命中，或深挖未执行）")
    # 未纳入精读的候选必须显名（SKILL Step 3 第 7 点）：不写出来，读者会以为
    # 所有预警都精读过了。「深挖候选」由预算与级别决定，剩下的是可手动触发的。
    undug = [c for c in m.get("深挖候选", []) if c["问题点"] not in (summaries or {})]
    if undug:
        lines += ["", f"本月另有 {len(undug)} 个预警诉点未纳入精读（受深挖预算限制），"
                      "可按需手动触发专题深挖：", ""]
        lines += [f"- {c['问题点']}（{c['级别']}色预警，{c['条数']}条）" for c in undug]
    # 叙述.json 中的自定义额外章节追加为 md 附录
    if narrative:
        extra = report_outline.extra_titles(narrative)
        if extra:
            lines.append("\n## 专项说明附录\n")
            for title in extra:
                c = narrative["章节"][title]
                lines += [f"### {title}", mark(c.get("叙述", ""))]
                if c.get("表格"):
                    lines += ["", strip_tips(strip_markers(c["表格"]))]
                if c.get("洞察"):
                    lines.append(f"**洞察**：{strip_tips(strip_markers(c['洞察']))}")
                if c.get("风险提示"):
                    lines.append(f"**风险提示**：{strip_tips(strip_markers(c['风险提示']))}")
                lines.append("")
    if tf.order:
        lines.append("\n## 注释\n")
        lines += [f"[^{n}]: {text}" for n, _k, text in tf.order]
    return "\n".join(lines)

def build_alert_list(metrics):
    lines = [f"# 督办预警清单 · {metrics['月份']}", "",
             "> 仅含红色、橙色预警，可按条转发对应处室。数据来源：客户督办/投诉月度数据，金箍棒自动生成。", ""]
    for w in metrics["预警汇总"]:
        if w["级别"] not in ("红", "橙"):
            continue
        lines += [f"## {BADGE[w['级别']]} {w['问题点'] or w['依据'][:20]}",
                  f"- 级别：{w['级别']}（{w['表']}）", f"- 依据：{w['依据']}",
                  f"- 建议：请相关处室关注办理进度与同类问题源头治理", ""]
    return "\n".join(lines)

def build_alert_points(metrics, summaries):
    trend = metrics["模型"].get("督办投诉比照", {}).get("指标", {}).get("走势", {})
    lines = ["# 投诉预警点（近期）", "",
             f"> 金箍棒每月**覆盖式**更新，本版基于 {metrics['月份']} 数据，生成于 {metrics['生成时间']}。",
             "> 火眼金睛/照妖镜评估时：事项涉及下列业务的，逐条核对并在意见中回应。", ""]
    for w in metrics["预警汇总"]:
        if w["级别"] not in ("红", "橙") or not w["问题点"]:
            continue
        t = trend.get(w["问题点"], {})
        走势 = "、".join(f"{k}:{v}笔" for k, v in sorted(t.items())) or "见月报"
        提示 = summaries.get(w["问题点"], {}).get("归因", w["依据"])
        lines += [f"## {BADGE[w['级别']]} {w['问题点']}", f"- 级别：{w['级别']} | 近月走势：{走势}",
                  f"- 风险提示：{提示}", ""]
    return "\n".join(lines)

FORMAL_CSS = """html{scroll-behavior:smooth}
body{font-family:'Microsoft YaHei',sans-serif;margin:0;padding:0;color:#222;line-height:1.8}
.doc{max-width:860px;margin:0 auto;padding:0 24px 48px}
body.toc-open{padding-left:248px}
#toc{position:fixed;left:0;top:0;bottom:0;width:248px;overflow-y:auto;box-sizing:border-box;
background:#f7f8fa;border-right:1px solid #e2e5ea;padding:14px 0 24px;font-size:13px;
transform:translateX(-248px);transition:transform .18s;z-index:50}
body.toc-open #toc{transform:none}
#toc .toc-hd{display:flex;align-items:center;justify-content:space-between;padding:0 12px 10px;
margin-bottom:6px;border-bottom:1px solid #e2e5ea;font-weight:600;color:#1a4d8f}
#toc button,#toc-btn{border:1px solid #ccd2da;background:#fff;color:#555;cursor:pointer;
border-radius:3px;font-size:13px;line-height:1;padding:4px 7px}
#toc ul{list-style:none;margin:0;padding:0}
#toc a{display:block;padding:5px 12px 5px 0;color:#333;text-decoration:none}
#toc a:hover{background:#e9eef6;color:#1a4d8f}
#toc .t2{display:flex;flex-wrap:wrap;align-items:flex-start;padding-top:2px}
#toc .t2>a{flex:1;padding-left:2px;font-weight:600}
#toc .t2>ul{flex-basis:100%}
#toc .t3 a{padding-left:32px;color:#5a616b;font-size:12.5px}
#toc .tw{display:inline-block;width:18px;text-align:center;cursor:pointer;color:#8a9199;
user-select:none;padding-top:5px}
#toc li.toc-fold>ul{display:none}
#toc li.toc-fold>.tw{transform:rotate(-90deg)}
#toc-btn{position:fixed;left:10px;top:10px;z-index:60;padding:6px 10px}
body.toc-open #toc-btn{display:none}
@media print{#toc,#toc-btn{display:none}body.toc-open{padding-left:0}}
.cover{text-align:center;padding:64px 0 48px;border-bottom:3px solid #1a4d8f;margin-bottom:32px}
.cover .eyebrow{font-size:14px;letter-spacing:.3em;color:#999;margin-bottom:12px}
.cover .dept{font-size:26px;font-weight:600}.cover .title{font-size:22px;margin-top:6px}
.cover .date{font-size:14px;color:#888;margin-top:14px}
h2{font-size:18px;border-left:4px solid #1a4d8f;padding-left:10px;margin:32px 0 14px}
table{border-collapse:collapse;width:100%;margin:12px 0;font-size:14px}
th,td{border:1px solid #ccc;padding:6px 10px;text-align:left}th{background:#f5f5f5}
.finding-box{background:#fdf6ea;border:1px solid #e8d6a8;border-left:4px solid #c9891a;
border-radius:2px;padding:18px 22px;margin-bottom:20px}
.finding-box .label{font-weight:600;color:#a3690f;margin-bottom:10px}
.insight-box{background:#eef4fb;border:1px solid #bcd4ec;border-left:4px solid #1a4d8f;
border-radius:2px;padding:16px 20px;margin:18px 0}
.insight-box .label{font-weight:600;color:#1a4d8f;margin-bottom:6px}
.risk-box{background:#fbeceb;border:1px solid #e8b8b4;border-left:4px solid #b8202e;
border-radius:2px;padding:16px 20px;margin:18px 0}
.risk-box .label{font-weight:600;color:#a3231b;margin-bottom:6px}
.suggestion h4{color:#1a4d8f;margin-bottom:2px}
.footer{text-align:center;color:#aaa;font-size:12px;margin-top:48px;padding-top:16px;
border-top:1px solid #eee}
.note-line{color:#999;font-size:12px;margin:4px 0}
sup.fn{color:#1a4d8f;font-weight:600;font-size:11px;padding-left:1px;cursor:help;
position:relative}
sup.fn .fn-tip{display:none;position:absolute;left:0;top:1.5em;z-index:30;
width:min(400px,84vw);background:#1f2a37;color:#fff;border-radius:4px;padding:8px 11px;
font-size:12px;font-weight:400;line-height:1.65;text-align:left;word-break:break-word;
box-shadow:0 4px 14px rgba(0,0,0,.28)}
sup.fn:hover .fn-tip,sup.fn:focus .fn-tip{display:block}
.fn-list{border-top:1px solid #ddd;margin-top:36px;padding-top:12px;color:#555;font-size:13px}
.fn-list li{margin-bottom:6px}
.mask{border-bottom:1px dashed #b8202e;color:#a3231b;cursor:help;position:relative}
.mask .mask-body{display:none;position:absolute;left:0;top:1.7em;z-index:30;
width:min(560px,88vw);max-height:340px;overflow-y:auto;background:#fff;color:#333;
border:1px solid #b8202e;border-radius:3px;padding:10px 12px;font-size:12.5px;
font-weight:400;line-height:1.65;text-align:left;word-break:break-word;
box-shadow:0 6px 20px rgba(0,0,0,.2)}
.mask:hover .mask-body,.mask:focus .mask-body{display:block}
.mask .m-i{display:block;padding:4px 0;border-bottom:1px dotted #e6e6e6}
.mask .m-i:last-child{border-bottom:none}
.gl{border-bottom:1px dotted #1a4d8f;cursor:help;position:relative}
.gl-mk{font-size:10px;vertical-align:super;margin-left:1px;opacity:.7;
border-bottom:none;text-decoration:none}
.gl .gl-tip{display:none;position:absolute;left:0;top:1.6em;z-index:30;
width:min(430px,86vw);background:#1f2a37;color:#fff;border-radius:4px;padding:9px 12px;
font-size:12px;font-weight:400;line-height:1.65;text-align:left;word-break:break-word;
box-shadow:0 4px 14px rgba(0,0,0,.28)}
.gl:hover .gl-tip,.gl:focus .gl-tip{display:block}"""

PH = "\x00%d\x00"


def _stash_spans(html, cls, vault):
    """按 <span>/</span> 深度配对整块摘出（mask 里嵌着 m-i，非贪婪正则会截错）。"""
    out, i, tag = [], 0, '<span class="%s"' % cls
    while True:
        j = html.find(tag, i)
        if j < 0:
            out.append(html[i:])
            return "".join(out)
        out.append(html[i:j])
        k, depth = j, 0
        while k < len(html):
            if html.startswith("<span", k):
                depth += 1
                k = html.index(">", k) + 1
            elif html.startswith("</span>", k):
                depth -= 1
                k += 7
                if depth == 0:
                    break
            else:
                k += 1
        vault.append(html[j:k])
        out.append(PH % (len(vault) - 1))
        i = k


def _gloss_section(sec, terms):
    """一节内每个术语只标首次出现，且不碰标题、不碰已有的悬浮窗。"""
    vault = []

    def keep(m):
        vault.append(m.group(0))
        return PH % (len(vault) - 1)

    # 顺序要紧：先摘 sup（里面含 fn-tip），再摘 mask 整块，最后摘标题与文末注释表
    sec = _re.sub(r'<sup class="fn".*?</sup>', keep, sec, flags=_re.S)
    sec = _stash_spans(sec, "mask", vault)
    sec = _re.sub(r"<h[23][^>]*>.*?</h[23]>", keep, sec, flags=_re.S)
    sec = _re.sub(r'<div class="fn-list">.*?</div>', keep, sec, flags=_re.S)

    for word, desc in terms:
        chunks = _re.split(r"(<[^>]+>)", sec)
        for i, c in enumerate(chunks):
            if c.startswith("<") or word not in c:
                continue
            span = ('<span class="gl" tabindex="0">%s<span class="gl-mk">&#128269;</span>'
                    '<span class="gl-tip">%s</span></span>'
                    % (word, _html.escape(desc)))
            vault.append(span)
            chunks[i] = c.replace(word, PH % (len(vault) - 1), 1)
            sec = "".join(chunks)
            break
    for n in range(len(vault) - 1, -1, -1):     # 倒序还原：占位符可能互相嵌套
        sec = sec.replace(PH % n, vault[n])
    return sec


def _mark_glossary(body, terms):
    """给正文里的预警级别与分析模型挂术语悬浮（用户 2026-07-25）。

    跳过封面与「报告说明」章——定义本身就写在那一章，再挂悬浮是自我循环。
    """
    secs = _re.split(r"(?=<h2)", body)
    return "".join(s if i <= 1 else _gloss_section(s, terms)
                   for i, s in enumerate(secs))


def _link_refs(body, heads):
    """附件清单表「对应正文」列做成锚点（用户 2026-07-25）。

    单元格里写章节名（不带序号），这里按「实际标题以它结尾」匹配到对应 id。
    序号是渲染时才编的，写死在叙述.json 里下个月就会错位。匹配不到就原样留着，
    宁可不跳也不瞎链。
    """
    m = _re.search(r'<h2 id="[^"]+">[^<]*附件清单</h2>(.*?)(?=<h2|\Z)', body, _re.S)
    if not m:
        return body

    def cell(mm):
        txt = mm.group(1).strip()
        if len(txt) < 4:
            return mm.group(0)
        for hid, htext in heads:
            if htext.endswith(txt):
                return '<td><a href="#%s">%s</a></td>' % (hid, mm.group(1))
        return mm.group(0)

    sec = _re.sub(r"<td>([^<]+)</td>", cell, m.group(1))
    return body[:m.start(1)] + sec + body[m.end(1):]


def _inject_toc(body):
    """给正文 h2/h3 编 id 并生成左侧目录（收到 h3，即（一）（二）这层）。

    在装配好的 html 上后处理，而不是在每个 emit 点手工挂 id——emit 点有十来处
    （章节标题、md_to_html 的 ### 小节等），逐个改必漏，漏一个目录项就点不动。
    """
    items, cur = [], [0, 0]

    def repl(m):
        lvl, inner = int(m.group(1)), m.group(2)
        if lvl == 2:
            cur[0] += 1
            cur[1] = 0
            hid = "sec-%d" % cur[0]
        else:
            cur[1] += 1
            hid = "sec-%d-%d" % (cur[0], cur[1])
        items.append((lvl, hid, _re.sub(r"<[^>]+>", "", inner).strip()))
        return '<h%d id="%s">%s</h%d>' % (lvl, hid, inner, lvl)

    body = _re.sub(r"<h([23])>(.*?)</h\1>", repl, body, flags=_re.S)
    body = _link_refs(body, [(hid, text) for _lvl, hid, text in items])
    if not items:
        return body, ""
    li, open_ul = [], False
    for lvl, hid, text in items:
        link = '<a href="#%s">%s</a>' % (hid, _html.escape(text))
        if lvl == 2:
            if li:
                li.append("</ul></li>" if open_ul else "</li>")
            li.append('<li class="t2"><span class="tw">&#9662;</span>' + link)
            open_ul = False
        else:
            if not open_ul:
                li.append("<ul>")
                open_ul = True
            li.append('<li class="t3">%s</li>' % link)
    li.append("</ul></li>" if open_ul else "</li>")
    return body, ('<nav id="toc"><div class="toc-hd"><span>目录</span>'
                  '<button id="toc-x" title="收起目录">&#171;</button></div><ul>'
                  + "".join(li) + "</ul></nav>"
                  + '<button id="toc-btn" title="展开目录">&#9776; 目录</button>')


def _chart_img_tag(chart):
    if not chart:
        return ""
    if chart["type"] == "bar":
        png = chart_images.bar_chart_png(chart["labels"], chart["series"], chart["title"],
                                          xlabel=chart.get("xlabel"))
    else:
        png = chart_images.line_chart_png(chart["series"], chart["title"])
    if not png:
        return ""
    b64 = base64.b64encode(png).decode("ascii")
    return f'<div style="text-align:center;margin:16px 0"><img src="data:image/png;base64,{b64}" style="max-width:100%"/></div>'

def build_formal_html(metrics, summaries, narrative):
    tf = TextFootnotes(report_notes.footnotes(metrics))

    def _sup(n, k):
        # 注文直接挂在上标上：读者不必翻到文末注释表（用户 2026-07-25 提）
        return (f'<sup class="fn" tabindex="0">[{n}]'
                f'<span class="fn-tip">{_html.escape(tf.notes.get(k, ""))}</span></sup>')

    def _mask(label, body):
        # body 已在上游被转义过；‖ 是条目分隔符
        items = "".join(f'<span class="m-i">{x}</span>' for x in body.split("‖") if x.strip())
        return (f'<span class="mask" tabindex="0">{label}'
                f'<span class="mask-body">{items}</span></span>')

    tip = lambda s: sub_tips(s, _mask)
    mark = lambda t: tip(tf.sub(_html.escape(t), _sup))      # 纯文本：先转义再落注
    mark_html = lambda h: tip(tf.sub(h, _sup))               # md_to_html 已转义过的片段
    CN_NUM = ["一", "二", "三", "四", "五", "六", "七", "八",
              "九", "十", "十一", "十二", "十三", "十四"]
    no = iter(CN_NUM)
    parts = [f'<div class="cover"><div class="eyebrow">CUSTOMER COMPLAINT ANALYSIS</div>'
             f'<div class="dept">总行数字运营部</div><div class="title">客户投诉分析报告</div>'
             f'<div class="date">（{_html.escape(report_notes.period_label(metrics["月份"]))}）'
             f'</div></div>']

    intro = report_notes.build_intro(metrics)
    parts.append(f"<h2>{next(no)}、{_html.escape(intro['title'])}</h2>")
    parts.append(mark_html(md_to_html(intro["table_md"])))

    parts.append(f"<h2>{next(no)}、结论摘要</h2>")
    findings = narrative.get("关键发现速览", [])
    if findings:
        rows = "".join(f"<p><b>{_html.escape(f['标签'])}：</b>{mark(f['文本'])}</p>"
                       for f in findings)
        parts.append(f'<div class="finding-box"><div class="label">★ 关键发现速览</div>{rows}</div>')
    for line in narrative.get("结论摘要", []):
        parts.append(f"<p>{mark(line)}</p>")

    outline, appendix = report_outline.split_appendix(
        report_outline.build_outline(metrics, summaries, narrative))

    def emit(sec):
        parts.append(f"<h2>{next(no)}、{_html.escape(sec['title'])}</h2>")
        if sec["narrative"]:
            # 走 md_to_html：叙述里的换行各自成段、'- ' 成列表、**加粗**生效
            # （此前硬包一个 <p>，分段分点全失效——用户 2026-07-25）
            parts.append(mark_html(md_to_html(sec["narrative"])))
        if sec["insight"]:
            parts.append(f'<div class="insight-box"><div class="label">■ 数据洞察</div>'
                         f'<p>{mark(sec["insight"])}</p></div>')
        if sec["risk"]:
            parts.append(f'<div class="risk-box"><div class="label">⚠ 风险提示</div>'
                         f'<p>{mark(sec["risk"])}</p></div>')
        parts.append(mark_html(md_to_html(sec["table_md"])))
        parts.append(_chart_img_tag(sec["chart"]))
        if sec.get("note"):
            # 用 extend 不用 +=：嵌套函数里的 += 会把 parts 当成局部变量
            parts.extend(f'<p class="note-line">{_html.escape(line)}</p>'
                         for line in sec["note"].split(chr(10)))

    for sec in outline:
        emit(sec)

    parts.append(f"<h2>{next(no)}、策略建议</h2>")
    for s in narrative.get("策略建议", []):
        parts.append(f'<div class="suggestion"><h4>{_html.escape(s["标题"])}</h4>'
                     f'<p>{mark(s["内容"])}</p></div>')

    for sec in appendix:       # 附件清单固定排最后（用户 2026-07-25）
        emit(sec)

    if tf.order:
        items = "".join(f"<li>[{n}] {_html.escape(text)}</li>" for n, _k, text in tf.order)
        # 列表不自动编号：条目自带的 [n] 要与正文上标对齐，<ol> 的 1. 2. 会与之撞成「1. [1]」
        parts.append(f'<div class="fn-list"><b>注释</b>'
                     f'<ol style="list-style:none;padding-left:0;margin-top:8px">{items}</ol></div>')

    parts.append(f'<div class="footer">生成：{_html.escape(metrics["生成时间"])} · '
                 f'总行数字运营部声誉风险管理智能体·悟空（金箍棒）</div>')

    body = _mark_glossary("\n".join(parts), report_notes.glossary(metrics))
    body, nav = _inject_toc(body)
    return (f'<!DOCTYPE html>\n<html lang="zh"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>客户投诉分析报告 {_html.escape(metrics["月份"])}</title>'
            f'<style>{FORMAL_CSS}</style></head><body>{nav}'
            f'<div class="doc">{body}</div>'
            f'<script>{PAGE_JS}</script></body></html>')


# 蒙版默认从上标左缘向右展开，靠近版心右界的会溢出到版面外——读者得横向拖滚动条，
# 而一拖鼠标就离开触发元素、蒙版随即消失（用户 2026-07-25 反馈）。
# 悬停/聚焦时按版心内容框夹一次：越右界就整体左移越界量，再兜一次左界。
# 纯 CSS 做不到（无法感知元素距边界多远），故用页内脚本，不引任何外部资源。
PAGE_JS = """
document.querySelectorAll('sup.fn,.mask,.gl').forEach(function(h){
 var tip=h.querySelector('.fn-tip,.mask-body,.gl-tip'); if(!tip) return;
 function clamp(){
  // 量之前先强制可见：若 :hover 样式尚未生效，量到的是 0×0，会把蒙版推到版心外
  var prev=tip.style.display; tip.style.display='block';
  tip.style.left='0px';
  var d=document.querySelector('.doc')||document.body;
  var cs=getComputedStyle(d), b=d.getBoundingClientRect();
  var right=b.right-parseFloat(cs.paddingRight), left=b.left+parseFloat(cs.paddingLeft);
  var over=tip.getBoundingClientRect().right-right;
  if(over>0) tip.style.left=(-over)+'px';
  var under=left-tip.getBoundingClientRect().left;
  if(under>0) tip.style.left=(parseFloat(tip.style.left)+under)+'px';
  tip.style.display=prev;
 }
 h.addEventListener('mouseenter',clamp);
 h.addEventListener('focus',clamp);
});
// 左侧目录：整体收起/展开 + 分节折叠。窄屏默认收起，免得压住正文
var B=document.body;
if(innerWidth>=1180) B.classList.add('toc-open');
var x=document.getElementById('toc-x'), o=document.getElementById('toc-btn');
if(x) x.onclick=function(){B.classList.remove('toc-open');};
if(o) o.onclick=function(){B.classList.add('toc-open');};
document.querySelectorAll('#toc .tw').forEach(function(w){
 w.onclick=function(){w.parentNode.classList.toggle('toc-fold');};
});
"""

def build_index(base, metrics):
    meta_p = base / "底库" / "_meta.json"
    meta = json.loads(meta_p.read_text(encoding="utf-8")) if meta_p.exists() else {"duban": {}, "tousu": {}}
    months = sorted(set(meta["duban"]) | set(meta["tousu"]))
    lvl = [w["级别"] for w in metrics["预警汇总"]]
    warn = f"红{lvl.count('红')}橙{lvl.count('橙')}黄{lvl.count('黄')}"
    lines = ["# 客户投诉分析 · 全貌",
             f"\n> 金箍棒每次运行**覆盖式**自动生成（{datetime.now():%Y-%m-%d %H:%M}），手改内容下次运行会丢失；"
             f"三层结构：本页（全貌）→ 报告/（月度）→ 底库/（明细）。",
             f"\n**最近分析**：{metrics['月份']}（预警 {warn}）",
             f"\n**映射待补**：{'、'.join(meta.get('未映射主办单位', [])) or '无'}",
             "\n## 底库现状\n",
             "| 月份 | 督办条数 | 投诉条数 |", "|---|---|---|"]
    for mo in months:
        lines.append(f"| {mo} | {meta['duban'].get(mo, {}).get('条数', '-')} | "
                     f"{meta['tousu'].get(mo, {}).get('条数', '-')} |")
    lines += ["\n## 历次报告\n"] + [f"- [{d.name}](报告/{d.name}/月度分析报告.md)"
                                    for d in sorted((base / "报告").glob("20*")) if d.is_dir()]
    return "\n".join(lines)

def run(report_dir, config):
    report_dir = Path(report_dir)
    metrics = json.loads((report_dir / "指标.json").read_text(encoding="utf-8"))
    sp = report_dir / "摘要.json"
    summaries = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else {}
    sw = config.get("产出物开关", {})
    base = Path(config["路径"]["数据区"])
    np_ = report_dir / "叙述.json"
    narrative = json.loads(np_.read_text(encoding="utf-8")) if np_.exists() else {}
    md = build_md(metrics, summaries, narrative)
    if sw.get("md报告", True):
        (report_dir / "月度分析报告.md").write_text(md, encoding="utf-8")
    if sw.get("预警清单", True):
        (report_dir / "督办预警清单.md").write_text(build_alert_list(metrics), encoding="utf-8")
    if sw.get("预警点文件", True):
        pp = Path(config["路径"]["预警点文件"])
        pp.parent.mkdir(parents=True, exist_ok=True)
        pp.write_text(build_alert_points(metrics, summaries), encoding="utf-8")
    if sw.get("html报告", True):
        (report_dir / "月度分析报告.html").write_text(
            build_formal_html(metrics, summaries, narrative), encoding="utf-8")
    (base / "INDEX.md").write_text(build_index(base, metrics), encoding="utf-8")

if __name__ == "__main__":
    cfg = yaml.safe_load(Path(sys.argv[2]).read_text(encoding="utf-8"))
    run(sys.argv[1], cfg)
    print("渲染完成")
