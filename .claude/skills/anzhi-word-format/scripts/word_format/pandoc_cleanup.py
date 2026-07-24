# word_format/pandoc_cleanup.py
"""
pandoc_cleanup.py
清理来自 pandoc（markdown → docx）转换的遗留样式污染。
默认无条件调用：对不含这些样式的普通 docx 是安全无操作。
"""
from __future__ import annotations

from docx import Document
from docx.oxml.ns import qn

from word_format.report_types import FormatReport

_HEADING_STYLE_IDS = [f"Heading{i}" for i in range(1, 6)] + \
                     [f"Heading{i}Char" for i in range(1, 6)]


def clean_heading_theme_color(doc: Document, report: FormatReport) -> None:
    """把 Heading1-5（含 Char 字符样式变体，共 10 个 styleId）的字体颜色强制改为纯黑。

    pandoc 默认 docx 模板给这些样式写入主题蓝
    （<w:color w:themeColor="accent1" w:themeShade="BF" w:val="0F4761"/>），
    公文标题应为纯黑。本函数在 styles.xml 层面清理，不管段落是否还引用该样式。

    注意：样式表是独立的 OOXML part，必须用 doc.styles.element 定位，
    不能用 doc.element.find(qn("w:styles"))——后者恒为 None（会静默空跑）。
    """
    styles_el = doc.styles.element
    if styles_el is None:
        return
    n_fixed = 0
    for style_el in styles_el.findall(qn("w:style")):
        style_id = style_el.get(qn("w:styleId"), "")
        if style_id not in _HEADING_STYLE_IDS:
            continue
        rPr = style_el.find(qn("w:rPr"))
        if rPr is None:
            continue
        color_el = rPr.find(qn("w:color"))
        if color_el is None:
            continue
        has_theme = color_el.get(qn("w:themeColor")) is not None
        is_black = (color_el.get(qn("w:val")) or "").upper() == "000000"
        if not has_theme and is_black:
            continue                      # 已是纯黑且无主题色，跳过（保证幂等）
        for attr in list(color_el.attrib):
            del color_el.attrib[attr]     # 连 themeColor/themeShade 一并清掉
        color_el.set(qn("w:val"), "000000")
        n_fixed += 1
    if n_fixed:
        report.add("style", "fix",
                   f"清理 pandoc 标题主题色：{n_fixed} 处 Heading 样式改为纯黑")
