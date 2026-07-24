# word_format/word_format_tool.py
"""
word_format_tool.py
Word 格式整理主入口。
"""
from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path

try:  # Windows 控制台默认 GBK，报告里的 ✓/→/⚠ 等符号会导致 UnicodeEncodeError
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from docx import Document

from word_format.template_loader import (
    load_format_config, load_text_check_config,
    list_templates, set_default_template, get_default_template_name,
)
from word_format.page_setup  import setup_page
from word_format.body_format import apply_body_format
from word_format.text_check  import run_checks
from word_format.pandoc_cleanup import clean_heading_theme_color
from word_format.officecli_bridge import (
    mark_outline_levels, insert_toc, refresh_toc, close_document, blacken_toc_heading,
)
from word_format.report_types import FormatReport, render_summary, render_verbose, save_report

MODULE_DIR  = Path(__file__).resolve().parent
INPUT_DIR   = MODULE_DIR / "input"
OUTPUT_DIR  = MODULE_DIR / "output"
HISTORY_DIR = MODULE_DIR / "history"


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)

    if args.page_only and args.style_only:
        print("错误：--page-only 和 --style-only 不能同时使用")
        sys.exit(1)

    if args.toc and args.page_only:
        print("错误：--toc 需要正文格式处理，不能与 --page-only 同时使用")
        sys.exit(1)

    # ── 前置动作：不处理文档，直接退出 ──────────────────────────────────────
    if args.list_templates:
        default = get_default_template_name()
        print("可用模板：")
        for name, desc in list_templates():
            marker = " [默认]" if name == default else ""
            print(f"  {name}{marker}  {desc}")
        sys.exit(0)

    if args.set_default:
        try:
            set_default_template(args.set_default)
            print(f"默认模板已设为：{args.set_default}")
            sys.exit(0)
        except FileNotFoundError as e:
            print(f"错误：{e}")
            sys.exit(1)

    # ── 确定输入文件 ─────────────────────────────────────────────────────────
    input_path = _resolve_input(args.input)
    if input_path is None:
        print(f"错误：未找到输入文件。请将 .docx 放入 {INPUT_DIR} 或用 --input 指定。")
        sys.exit(1)

    # ── 加载配置 ──────────────────────────────────────────────────────────────
    if args.interactive:
        from word_format.interactive import run_interactive
        fmt_config = run_interactive()
    else:
        fmt_config = load_format_config(args.template or None)
    check_config = load_text_check_config()

    # --fix-list 临时覆盖
    if args.fix_list:
        check_config = replace(check_config, fix_list=True)

    # --page-style 覆盖模板默认页码模式（check-only 不输出页码，跳过此块避免误报）
    if args.page_style and not args.check_only:
        style_map = {"日常": "daily", "公文": "official"}
        new_pn = replace(fmt_config.page.page_number,
                         mode=style_map[args.page_style])
        new_page = replace(fmt_config.page, page_number=new_pn)
        fmt_config = replace(fmt_config, page=new_page)
        if not args.page_number:
            print("提示：--page-style 仅在开启 --page-number 时生效，本次未输出页码")

    report = FormatReport(
        template_name=fmt_config.name,
        input_filename=input_path.name,
    )

    # ── check-only 模式 ───────────────────────────────────────────────────────
    if args.check_only:
        doc = Document(str(input_path))
        run_checks(doc, check_config, report)
        docx_path, report_path = _make_output_paths(input_path, OUTPUT_DIR)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        save_report(report, report_path)
        print(render_summary(report, report_path=report_path))
        if args.verbose:
            print(render_verbose(report))
        return

    # ── 正常处理 ──────────────────────────────────────────────────────────────
    doc = Document(str(input_path))
    do_page  = not args.style_only
    do_style = not args.page_only
    toc_anchor = None

    if do_page:
        setup_page(doc, fmt_config.page, report, add_page_number=args.page_number)

    if do_style:
        apply_body_format(doc, fmt_config.body, report,
                          line_pitch_pt=fmt_config.page.line_pitch_pt,
                          format_tables=args.format_table,
                          page_config=fmt_config.page,
                          wrap_title=not args.no_title_wrap)
        clean_heading_theme_color(doc, report)
        run_checks(doc, check_config, report)
        if args.toc:
            toc_anchor = mark_outline_levels(doc, fmt_config.body, report)

    docx_path, report_path = _make_output_paths(input_path, OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    doc.save(str(docx_path))

    if args.toc:
        insert_toc(docx_path, report, toc_anchor)
        refresh_toc(docx_path, report)
        close_document(docx_path, report)
        blacken_toc_heading(docx_path, report)

    save_report(report, report_path, output_docx=docx_path)

    print(render_summary(report, output_docx=docx_path, report_path=report_path))
    if args.verbose:
        print(render_verbose(report))

    _archive(input_path)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="word_format_tool",
                                     description="Word 文档格式整理工具")
    parser.add_argument("--input",          metavar="FILE")
    parser.add_argument("--template",       metavar="NAME")
    parser.add_argument("--set-default",    metavar="NAME")
    parser.add_argument("--list-templates", action="store_true")
    parser.add_argument("--interactive", "-i", action="store_true")
    parser.add_argument("--verbose",        action="store_true")
    parser.add_argument("--page-only",      action="store_true")
    parser.add_argument("--style-only",     action="store_true")
    parser.add_argument("--page-number",    action="store_true")
    parser.add_argument("--page-style",     choices=["日常", "公文"])
    parser.add_argument("--format-table",   action="store_true")
    parser.add_argument("--fix-list",       action="store_true")
    parser.add_argument("--check-only",     action="store_true")
    parser.add_argument("--no-title-wrap",  action="store_true")
    parser.add_argument("--toc",            action="store_true")
    return parser.parse_args(argv)


def _resolve_input(input_arg: str | None) -> Path | None:
    if input_arg:
        p = Path(input_arg)
        if not p.is_absolute():
            p = Path.cwd() / p
        return p if p.exists() else None
    docx_files = sorted(INPUT_DIR.glob("*.docx"),
                        key=lambda f: f.stat().st_mtime, reverse=True)
    if not docx_files:
        return None
    if len(docx_files) > 1:
        print(f"发现 {len(docx_files)} 个文件，本次仅处理最新的 {docx_files[0].name}")
    return docx_files[0]


def _make_output_paths(input_path: Path, output_dir: Path) -> tuple[Path, Path]:
    stem = input_path.stem
    docx_path   = output_dir / f"{stem}_formatted.docx"
    report_path = output_dir / f"{stem}_report.md"
    return docx_path, report_path


def _archive(input_path: Path) -> None:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_dir = HISTORY_DIR / ts
    archive_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(input_path), str(archive_dir / input_path.name))
    print(f"原始文件已归档：{archive_dir / input_path.name}")


if __name__ == "__main__":
    main()
