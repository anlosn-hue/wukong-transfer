# -*- coding: utf-8 -*-
"""渲染五件产出+INDEX。用法：python render_report.py <报告月份dir> <config.yaml>
读取 <dir>/指标.json + 可选 摘要.json；数据区/预警点路径取自 config。"""
import html as _html
import json, sys
from datetime import datetime
from pathlib import Path
import yaml
import chart_images, base64, report_notes, report_outline
from marker_utils import TextFootnotes, strip_markers

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
    t = _html.escape(t)
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
    mark = lambda t: tf.sub(t, lambda n, k: f"[^{n}]")
    intro = report_notes.build_intro(m)
    lines = [f"# 客户投诉分析月报 · {report_notes.period_label(m['月份'])}",
             f"\n> 生成：{m['生成时间']} · 金箍棒（anzhi-tousufenxi-jingubang）",
             "\n## 报告说明\n", mark(intro["table_md"]),
             "\n## 参数快照\n", "```yaml",
             yaml.safe_dump(m["参数快照"], allow_unicode=True, sort_keys=False).strip(), "```",
             "\n## 预警总览\n", "| 级别 | 表 | 问题点 | 依据 | 来源 |", "|---|---|---|---|---|"]
    for w in m["预警汇总"]:
        lines.append(f"| {BADGE[w['级别']]}{w['级别']} | {w['表']} | {w['问题点'] or '-'} | "
                     f"{w['依据']} | {w['来源模型']} |")
    if not m["预警汇总"]:
        lines.append("| - | - | 本月无预警 | - | - |")
    for name in MODEL_ORDER:
        if name in m["模型"]:
            lines += ["\n## " + MODEL_DISPLAY.get(name, name), "", m["模型"][name]["md"]]
    lines.append("\n## 归因摘要（L2 深挖）\n")
    if summaries:
        for p, s in summaries.items():
            subs = "；".join(f"{x['主题']}×{x['条数']}（{x['典型例']}）" for x in s.get("子问题", []))
            lines += [f"### {p}", f"- **归因**：{s.get('归因','')}", f"- **子问题**：{subs}",
                      f"- **处理对症性**：{s.get('处理对症','')}",
                      f"- **空处理结果占比**：{s.get('空处理结果占比','-')}", ""]
    else:
        lines.append("（本月无红/橙预警命中，或深挖未执行）")
    # 叙述.json 中的自定义额外章节追加为 md 附录
    if narrative:
        extra = report_outline.extra_titles(narrative)
        if extra:
            lines.append("\n## 专项说明附录\n")
            for title in extra:
                c = narrative["章节"][title]
                lines += [f"### {title}", mark(c.get("叙述", ""))]
                if c.get("表格"):
                    lines += ["", strip_markers(c["表格"])]
                if c.get("洞察"):
                    lines.append(f"**洞察**：{strip_markers(c['洞察'])}")
                if c.get("风险提示"):
                    lines.append(f"**风险提示**：{strip_markers(c['风险提示'])}")
                lines.append("")
    if tf.order:
        lines.append("\n## 注释\n")
        lines += [f"[^{n}]: {text}" for n, _k, text in tf.order]
    return "\n".join(lines)

def build_alert_list(metrics):
    lines = [f"# 督办预警清单 · {metrics['月份']}", "",
             "> 仅含红/橙预警，可按条转发对应处室。数据来源：客户督办/投诉月度数据，金箍棒自动生成。", ""]
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

FORMAL_CSS = """body{font-family:'Microsoft YaHei',sans-serif;max-width:860px;margin:0 auto;
padding:0 24px 48px;color:#222;line-height:1.8}
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
sup.fn{color:#1a4d8f;font-weight:600;font-size:11px;padding-left:1px}
.fn-list{border-top:1px solid #ddd;margin-top:36px;padding-top:12px;color:#555;font-size:13px}
.fn-list li{margin-bottom:6px}"""

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
    _sup = lambda n, k: f'<sup class="fn">[{n}]</sup>'
    mark = lambda t: tf.sub(_html.escape(t), _sup)          # 纯文本：先转义再落注
    mark_html = lambda h: tf.sub(h, _sup)                    # md_to_html 已转义过的片段
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

    outline = report_outline.build_outline(metrics, summaries, narrative)
    for sec in outline:
        parts.append(f"<h2>{next(no)}、{_html.escape(sec['title'])}</h2>")
        if sec["narrative"]:
            parts.append(f"<p>{mark(sec['narrative'])}</p>")
        if sec["insight"]:
            parts.append(f'<div class="insight-box"><div class="label">■ 数据洞察</div>'
                         f'<p>{mark(sec["insight"])}</p></div>')
        if sec["risk"]:
            parts.append(f'<div class="risk-box"><div class="label">⚠ 风险提示</div>'
                         f'<p>{mark(sec["risk"])}</p></div>')
        parts.append(mark_html(md_to_html(sec["table_md"])))
        parts.append(_chart_img_tag(sec["chart"]))
        if sec.get("note"):
            parts += [f'<p class="note-line">{_html.escape(line)}</p>' for line in sec["note"].split("\n")]

    parts.append(f"<h2>{next(no)}、策略建议</h2>")
    for s in narrative.get("策略建议", []):
        parts.append(f'<div class="suggestion"><h4>{_html.escape(s["标题"])}</h4>'
                     f'<p>{mark(s["内容"])}</p></div>')

    if tf.order:
        items = "".join(f"<li>[{n}] {_html.escape(text)}</li>" for n, _k, text in tf.order)
        parts.append(f'<div class="fn-list"><b>注释</b><ol style="padding-left:20px">{items}</ol></div>')

    parts.append(f'<div class="footer">生成：{_html.escape(metrics["生成时间"])} · '
                 f'总行数字运营部声誉风险管理智能体·悟空（金箍棒）</div>')

    body = "\n".join(parts)
    return (f'<!DOCTYPE html>\n<html lang="zh"><head><meta charset="utf-8">'
            f'<title>客户投诉分析报告 {_html.escape(metrics["月份"])}</title>'
            f'<style>{FORMAL_CSS}</style></head><body>{body}</body></html>')

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
