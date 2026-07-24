# -*- coding: utf-8 -*-
"""报告渲染：清单.json + 研判.json + 发酵.json → 报告.md。
研判/发酵缺失时降级（只出 A 层清单），实事求是不编造。
用法：python render_report.py --outdir <目录>"""
import argparse, json, sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from contract import notes_from_json

def _load(d, name):
    p = Path(d) / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

def 执行(*, 输出目录):
    d = Path(输出目录)
    清单 = _load(d, "清单.json")
    研判 = {r["id"]: r for r in _load(d, "研判.json").get("研判", [])}
    发酵 = {f["id"]: f for f in _load(d, "发酵.json").get("发酵", [])}
    q = 清单.get("查询", {})
    notes = notes_from_json(清单)
    命中 = [n for n in notes if n.命中筛选]

    L = []
    L.append(f"# 红孩儿 · 小红书风险快照 — {q.get('关键词','')}")
    L.append("")
    L.append(f"- 查询时间：{date.today().isoformat()}")
    L.append(f"- 关键词：{q.get('关键词','')} ｜ 时间窗：{q.get('时间窗天数','')} 天 ｜ 通道：{q.get('通道','')}")
    L.append(f"- 抓取笔记 {len(notes)} 篇，A 层命中 {len(命中)} 篇")
    L.append("")
    L.append("> 内部舆情参考，红孩儿自有小号只读采集，不对外发布。")
    L.append("")

    if not 命中:
        L.append("## 结论：无命中")
        L.append("")
        L.append("本次查询在时间窗内未发现命中风险筛选的小红书笔记。")
        (d / "报告.md").write_text("\n".join(L), encoding="utf-8")
        return

    L.append("## 一、A 层命中清单")
    L.append("")
    L.append("| 标题 | 作者 | 发布 | 点赞 | 收藏 | 评论 | 命中原因 | 链接 |")
    L.append("|------|------|------|------|------|------|---------|------|")
    for n in 命中:
        L.append(f"| {n.标题} | {n.作者} | {n.发布时间} | {n.点赞} | {n.收藏} | {n.评论} "
                 f"| {'；'.join(n.筛选原因)} | [原帖]({n.链接}) |")
    L.append("")

    研判命中 = [n for n in 命中 if n.id in 研判]
    if 研判命中:
        L.append("## 二、B 层研判")
        L.append("")
        for n in 研判命中:
            r = 研判[n.id]
            L.append(f"### {n.标题}")
            L.append(f"- 情绪：{r.get('情绪','')} ｜ 涉我行：{'是' if r.get('涉我行') else '否'} "
                     f"｜ 风险性质：{r.get('风险性质','')} ｜ 高风险：{'是' if r.get('高风险') else '否'}")
            if r.get("摘录"):
                L.append(f"- 摘录：{r['摘录']}")
            if r.get("研判说明"):
                L.append(f"- 研判：{r['研判说明']}")
            L.append(f"- 原帖：{n.链接}")
            L.append("")

    if 发酵:
        L.append("## 三、C 层评论发酵度")
        L.append("")
        for nid, f in 发酵.items():
            标题 = next((n.标题 for n in 命中 if n.id == nid), nid)
            L.append(f"### {标题}")
            L.append(f"- 发酵度：{f.get('发酵度','')} ｜ 群体信号：{'有' if f.get('群体信号') else '无'}")
            if f.get("复现表述"):
                L.append(f"- 复现表述：{'、'.join(f['复现表述'])}")
            if f.get("说明"):
                L.append(f"- 说明：{f['说明']}")
            L.append("")

    (d / "报告.md").write_text("\n".join(L), encoding="utf-8")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()
    执行(输出目录=args.outdir)
    print("报告已生成：", str(Path(args.outdir) / "报告.md"))

if __name__ == "__main__":
    main()
