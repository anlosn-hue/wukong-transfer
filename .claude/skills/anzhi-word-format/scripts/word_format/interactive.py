# word_format/interactive.py
"""
interactive.py
Rich + questionary 交互式模板选择与参数调整。
非 TTY 环境自动退出，返回默认配置。
"""
from __future__ import annotations

import sys
from dataclasses import replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console

from word_format.config_types import FormatConfig
from word_format.template_loader import (
    load_format_config, list_templates, get_default_template_name,
    set_default_template, TEMPLATES_DIR,
)


def run_interactive() -> FormatConfig:
    """交互式选择模板和参数，返回 FormatConfig。非 TTY 时直接返回默认配置。"""
    if not sys.stdin.isatty():
        return load_format_config()

    try:
        import questionary
        from rich.console import Console
    except ImportError:
        print("提示：安装 rich 和 questionary 可启用交互模式。使用默认模板继续。")
        return load_format_config()

    console = Console()
    default_name = get_default_template_name()
    templates = list_templates()
    choices = [
        f"{name}{'  [默认]' if name == default_name else ''}  {desc}"
        for name, desc in templates
    ]

    try:
        selected = questionary.select("选择模板：", choices=choices).ask()
    except Exception:
        # 无控制台（如管道/重定向）时降级到默认配置
        return load_format_config()
    if selected is None:
        return load_format_config()

    selected_name = selected.split("  ")[0].strip()
    config = load_format_config(selected_name)

    _show_config_table(console, config)

    action = questionary.select(
        "操作：",
        choices=["直接运行", "修改参数", "设为默认并运行"]
    ).ask()

    if action is None:
        return load_format_config()

    if action == "设为默认并运行":
        set_default_template(selected_name)
        console.print(f"[green]已设为默认：{selected_name}[/green]")
        return config

    if action == "修改参数":
        config = _modify_params(console, config)

    return config


def _show_config_table(console: Console, config: FormatConfig) -> None:
    from rich.table import Table
    table = Table(title=f"模板：{config.name}", show_header=True)
    table.add_column("参数", style="cyan")
    table.add_column("当前值", style="green")

    p = config.page
    rows = [
        ("纸张宽度", f"{p.page_width_cm} cm"),
        ("纸张高度", f"{p.page_height_cm} cm"),
        ("上边距", f"{p.margin_top_cm} cm"),
        ("下边距", f"{p.margin_bottom_cm} cm"),
        ("左边距", f"{p.margin_left_cm} cm"),
        ("右边距", f"{p.margin_right_cm} cm"),
        ("网格字体", p.grid_font),
        ("网格字号", f"{p.grid_font_pt} pt"),
        ("每行字数", str(p.chars_per_line)),
        ("行距", f"{p.line_pitch_pt} pt"),
        ("主标题字体", config.body.main_title.font),
        ("主标题字号", f"{config.body.main_title.size_pt} pt"),
    ]
    for name, val in rows:
        table.add_row(name, val)
    console.print(table)


_EDITABLE_FIELDS = {
    "上边距 (margin_top_cm)":    ("page", "margin_top_cm",    float),
    "下边距 (margin_bottom_cm)": ("page", "margin_bottom_cm", float),
    "左边距 (margin_left_cm)":   ("page", "margin_left_cm",   float),
    "右边距 (margin_right_cm)":  ("page", "margin_right_cm",  float),
    "每行字数 (chars_per_line)": ("page", "chars_per_line",   int),
    "行距pt (line_pitch_pt)":    ("page", "line_pitch_pt",    float),
    "网格字体 (grid_font)":      ("page", "grid_font",        str),
}


def _modify_params(console: Console, config: FormatConfig) -> FormatConfig:
    import questionary

    while True:
        field_choice = questionary.select(
            "选择要修改的参数（选 完成 退出）：",
            choices=list(_EDITABLE_FIELDS.keys()) + ["完成"]
        ).ask()
        if field_choice is None or field_choice == "完成":
            break

        section, attr, cast = _EDITABLE_FIELDS[field_choice]
        section_obj = getattr(config, section)
        current = getattr(section_obj, attr)
        new_val_str = questionary.text(
            f"新值（当前：{current}）：", default=str(current)
        ).ask()
        if new_val_str is None:
            continue
        try:
            new_val = cast(new_val_str)
        except (ValueError, TypeError):
            console.print(f"[red]无效值：{new_val_str}[/red]")
            continue

        new_section = replace(section_obj, **{attr: new_val})
        config = replace(config, **{section: new_section})
        console.print(f"[green]{field_choice} → {new_val}[/green]")

    # 保存为新模板？
    save_name = questionary.text(
        "是否保存为新模板？（输入名称，或回车跳过）：", default=""
    ).ask()
    if save_name and save_name.strip():
        _save_as_new_template(config, save_name.strip(), console)

    return config


def _save_as_new_template(config: FormatConfig, name: str, console: Console) -> None:
    import yaml

    p = config.page
    b = config.body
    data = {
        "schema_version": 1,
        "name": name,
        "description": f"基于 {config.name} 修改",
        "page": {
            "page_width_cm": p.page_width_cm,
            "page_height_cm": p.page_height_cm,
            "margin_top_cm": p.margin_top_cm,
            "margin_bottom_cm": p.margin_bottom_cm,
            "margin_left_cm": p.margin_left_cm,
            "margin_right_cm": p.margin_right_cm,
            "header_dist_cm": p.header_dist_cm,
            "footer_dist_cm": p.footer_dist_cm,
            "grid_font": p.grid_font,
            "grid_font_pt": p.grid_font_pt,
            "chars_per_line": p.chars_per_line,
            "line_pitch_pt": p.line_pitch_pt,
            "page_number": {"mode": p.page_number.mode,
                            "font": p.page_number.font,
                            "size_pt": p.page_number.size_pt,
                            "align": p.page_number.align},
        },
        "body": {
            "main_title": {"font": b.main_title.font, "size_pt": b.main_title.size_pt},
            "sub_title":  {"font": b.sub_title.font,  "size_pt": b.sub_title.size_pt},
            "body":       {"font": b.body.font,        "size_pt": b.body.size_pt},
            "table":      {"font": b.table.font, "size_pt": b.table.size_pt,
                           "line_spacing_pt": b.table.line_spacing_pt},
            "headings": [
                {"level": h.level, "pattern": h.pattern,
                 "font": h.font, "size_pt": h.size_pt, "bold": h.bold}
                for h in b.headings
            ],
        },
    }
    out_path = TEMPLATES_DIR / f"{name}.yaml"
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
        console.print(f"[green]已保存：{out_path}[/green]")
    except OSError as e:
        console.print(f"[red]保存失败：{e}[/red]")
