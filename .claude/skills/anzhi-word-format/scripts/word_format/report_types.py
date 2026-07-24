# word_format/report_types.py
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class FormatEvent:
    category: str   # "page" | "body" | "text" | "leader" | "org" | "style"
    action: str     # "applied" | "fix" | "warning"
    detail: str


@dataclass
class FormatReport:
    template_name: str = ""
    input_filename: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))
    events: list[FormatEvent] = field(default_factory=list)

    def add(self, category: str, action: str, detail: str) -> None:
        self.events.append(FormatEvent(category, action, detail))

    @property
    def fix_count(self) -> int:
        return sum(1 for e in self.events if e.action == "fix")

    @property
    def warning_count(self) -> int:
        return sum(1 for e in self.events if e.action == "warning")

    def events_by(self, category: str) -> list[FormatEvent]:
        return [e for e in self.events if e.category == category]


def render_summary(report: FormatReport, output_docx: Path | None = None,
                   report_path: Path | None = None) -> str:
    lines = [
        "═══ 格式整理报告 ══════════════════════",
        f"文件：{report.input_filename}",
        f"模板：{report.template_name}    时间：{report.timestamp}",
        "",
    ]
    for ev in report.events_by("page"):
        lines.append(f"页面设置  {ev.detail}")
    for ev in report.events_by("body"):
        lines.append(f"正文格式  {ev.detail}")
    text_fixes = [e for e in report.events_by("text") if e.action == "fix"]
    if text_fixes:
        lines.append(f"文本校对  修改 {len(text_fixes)} 处")
    style_fixes = [e for e in report.events_by("style") if e.action == "fix"]
    if style_fixes:
        lines.append(f"样式清理  修改 {len(style_fixes)} 处")
    leader_warns = report.events_by("leader") + report.events_by("org")
    if leader_warns:
        lines.append(f"核查警告  {len(leader_warns)} 条")
    lines.append("──────────────────────────────────────")
    lines.append(f"修改 {report.fix_count} 处，警告 {report.warning_count} 条")
    if output_docx:
        lines.append(f"输出：{output_docx}")
    if report_path:
        lines.append(f"报告：{report_path}")
    return "\n".join(lines)


def render_verbose(report: FormatReport) -> str:
    sections: list[str] = []
    for cat, label in [("page", "页面设置"), ("body", "正文格式"),
                       ("text", "文本校对"), ("style", "样式清理"),
                       ("leader", "领导人核查"), ("org", "机构名称")]:
        evs = report.events_by(cat)
        if not evs:
            continue
        sections.append(f"### {label}")
        for ev in evs:
            prefix = "✓" if ev.action == "applied" else ("→" if ev.action == "fix" else "⚠")
            sections.append(f"  {prefix} {ev.detail}")
    return "\n".join(sections)


def save_report(report: FormatReport, path: Path, verbose: bool = True,
                output_docx: Path | None = None) -> None:
    lines = [
        "# 格式整理报告\n",
        f"**文件：** {report.input_filename}  ",
        f"**模板：** {report.template_name}  ",
        f"**时间：** {report.timestamp}  ",
    ]
    if output_docx is not None:
        lines.append(f"**产出文件路径：** {output_docx}\n")
    else:
        lines.append("")
    if verbose:
        lines.append(render_verbose(report))
    lines += [
        "\n---\n",
        f"**合计：** 修改 {report.fix_count} 处，警告 {report.warning_count} 条",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
