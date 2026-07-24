"""
page_setup.py
页面设置：纸张、页边距、页眉页脚距离、文档网格、可选页码。
所有参数从 PageConfig 读取，不再使用模块常量。
"""
from __future__ import annotations

from docx import Document
from docx.shared import Cm
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import copy

from word_format.config_types import PageConfig, PageNumberConfig
from word_format.report_types import FormatReport

OFFICIAL_PAGE_FONT = "宋体"
OFFICIAL_PAGE_SIZE_PT = 14.0      # 四号
OFFICIAL_DASH = "—"          # 一字线 —


def setup_page(doc: Document, config: PageConfig, report: FormatReport,
               add_page_number: bool = False) -> None:
    section = doc.sections[0]

    section.page_width  = Cm(config.page_width_cm)
    section.page_height = Cm(config.page_height_cm)
    section.top_margin    = Cm(config.margin_top_cm)
    section.bottom_margin = Cm(config.margin_bottom_cm)
    section.left_margin   = Cm(config.margin_left_cm)
    section.right_margin  = Cm(config.margin_right_cm)
    section.header_distance = Cm(config.header_dist_cm)
    section.footer_distance = Cm(config.footer_dist_cm)

    _set_doc_grid(doc, config)
    _set_default_font(doc, config)
    _set_normal_style_font(doc, config)

    if add_page_number:
        _add_page_numbers(doc, section, config.page_number)

    if add_page_number:
        mode_label_map = {
            "official": "；公文页码（— n —）",
            "daily": "；日常页码（第n页 共m页）",
        }
        mode_label = mode_label_map.get(config.page_number.mode, "；页码已添加")
    else:
        mode_label = ""

    report.add("page", "applied",
               f"已应用（{config.chars_per_line}字/行，行距{config.line_pitch_pt}磅）{mode_label}")


def _calc_char_space(config: PageConfig) -> int:
    """计算 OOXML charSpace：(charPitch_pt - fontSize_pt) × 4096"""
    text_w_pt = (config.page_width_cm - config.margin_left_cm - config.margin_right_cm) / 2.54 * 72
    char_pitch_pt = text_w_pt / config.chars_per_line
    return round((char_pitch_pt - config.grid_font_pt) * 4096)


def _set_doc_grid(doc: Document, config: PageConfig) -> None:
    line_pitch_twip = round(config.line_pitch_pt * 20)
    char_space = _calc_char_space(config)
    sectPr = _get_sectPr(doc)
    for old in sectPr.findall(qn("w:docGrid")):
        sectPr.remove(old)
    docGrid = OxmlElement("w:docGrid")
    docGrid.set(qn("w:type"),      "linesAndChars")
    docGrid.set(qn("w:linePitch"), str(line_pitch_twip))
    docGrid.set(qn("w:charSpace"), str(char_space))
    sectPr.append(docGrid)


def _set_default_font(doc: Document, config: PageConfig) -> None:
    styles_el = doc.element.find(qn("w:styles"))
    if styles_el is None:
        return
    docDefaults = styles_el.find(qn("w:docDefaults"))
    if docDefaults is None:
        docDefaults = OxmlElement("w:docDefaults")
        styles_el.insert(0, docDefaults)
    rPrDefault = _get_or_create(docDefaults, "w:rPrDefault")
    rPr        = _get_or_create(rPrDefault,  "w:rPr")
    _write_grid_font_to_rPr(rPr, config)


def _set_normal_style_font(doc: Document, config: PageConfig) -> None:
    styles_el = doc.element.find(qn("w:styles"))
    if styles_el is None:
        return
    for style_el in styles_el.findall(qn("w:style")):
        style_id = style_el.get(qn("w:styleId"), "")
        if style_id not in ("Normal", "a", "正文"):
            if not (style_el.get(qn("w:type")) == "paragraph"
                    and style_el.get(qn("w:default")) == "1"):
                continue
        rPr = style_el.find(qn("w:rPr"))
        if rPr is None:
            rPr = OxmlElement("w:rPr")
            style_el.append(rPr)
        _write_grid_font_to_rPr(rPr, config)


def _write_grid_font_to_rPr(rPr, config: PageConfig) -> None:
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.insert(0, rFonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia"):
        rFonts.set(qn(attr), config.grid_font)
    half_pts = str(int(config.grid_font_pt * 2))
    for ptag in ("w:sz", "w:szCs"):
        el = rPr.find(qn(ptag))
        if el is None:
            el = OxmlElement(ptag)
            rPr.append(el)
        el.set(qn("w:val"), half_pts)


def _add_page_numbers(doc, section, config: PageNumberConfig) -> None:
    if config.mode == "official":
        _add_official_page_numbers(doc, section)
    else:
        _add_daily_page_numbers(section, config)


def _add_daily_page_numbers(section, config: PageNumberConfig) -> None:
    align_map = {"center": "center", "left": "left", "right": "right"}
    jc_val = align_map.get(config.align, "center")
    line_pitch_twip = round(config.size_pt * 20 * 1.5)

    footer = section.footer
    footer.is_linked_to_previous = False
    fp = footer._element
    for child in list(fp):
        fp.remove(child)

    p = OxmlElement("w:p")
    fp.append(p)
    pPr = OxmlElement("w:pPr")
    p.append(pPr)
    jc = OxmlElement("w:jc")
    jc.set(qn("w:val"), jc_val)
    pPr.append(jc)
    spacing = OxmlElement("w:spacing")
    spacing.set(qn("w:line"),     str(line_pitch_twip))
    spacing.set(qn("w:lineRule"), "exact")
    spacing.set(qn("w:before"),   "0")
    spacing.set(qn("w:after"),    "0")
    pPr.append(spacing)

    _append_text_run(p, "第",    config.font, config.size_pt)
    _append_field(p, "PAGE",     config.font, config.size_pt)
    _append_text_run(p, "页 共", config.font, config.size_pt)
    _append_field(p, "NUMPAGES", config.font, config.size_pt)
    _append_text_run(p, "页",    config.font, config.size_pt)


def _add_official_page_numbers(doc, section) -> None:
    """GB/T 9704：奇数页居右、偶数页居左，宋体四号，`— N —`。"""
    doc.settings.odd_and_even_pages_header_footer = True
    _write_official_footer(section.footer, "right")          # 奇数页
    _write_official_footer(section.even_page_footer, "left")  # 偶数页


def _write_official_footer(footer, jc_val: str) -> None:
    footer.is_linked_to_previous = False
    fp = footer._element
    for child in list(fp):
        fp.remove(child)

    p = OxmlElement("w:p")
    fp.append(p)
    pPr = OxmlElement("w:pPr")
    p.append(pPr)
    jc = OxmlElement("w:jc")
    jc.set(qn("w:val"), jc_val)
    pPr.append(jc)
    line_pitch_twip = round(OFFICIAL_PAGE_SIZE_PT * 20 * 1.5)
    spacing = OxmlElement("w:spacing")
    spacing.set(qn("w:line"),     str(line_pitch_twip))
    spacing.set(qn("w:lineRule"), "exact")
    spacing.set(qn("w:before"),   "0")
    spacing.set(qn("w:after"),    "0")
    pPr.append(spacing)

    # `— ` + PAGE 域 + ` —`，数字左右各空一格
    _append_text_run(p, f"{OFFICIAL_DASH} ", OFFICIAL_PAGE_FONT, OFFICIAL_PAGE_SIZE_PT)
    _append_field(p, "PAGE",                 OFFICIAL_PAGE_FONT, OFFICIAL_PAGE_SIZE_PT)
    _append_text_run(p, f" {OFFICIAL_DASH}", OFFICIAL_PAGE_FONT, OFFICIAL_PAGE_SIZE_PT)


def _append_text_run(p, text: str, font: str, size_pt: float) -> None:
    r = OxmlElement("w:r")
    r.append(_make_rPr(font, size_pt))
    t = OxmlElement("w:t")
    t.text = text
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    r.append(t)
    p.append(r)


def _append_field(p, field_code: str, font: str, size_pt: float) -> None:
    rPr = _make_rPr(font, size_pt)
    for ftype in ("begin", "separate", "end"):
        r = OxmlElement("w:r")
        r.append(copy.deepcopy(rPr))
        fc = OxmlElement("w:fldChar")
        fc.set(qn("w:fldCharType"), ftype)
        r.append(fc)
        p.append(r)
        if ftype == "begin":
            r_instr = OxmlElement("w:r")
            r_instr.append(copy.deepcopy(rPr))
            instr = OxmlElement("w:instrText")
            instr.text = f" {field_code} "
            instr.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            r_instr.append(instr)
            p.append(r_instr)


def _make_rPr(font: str, size_pt: float):
    rPr = OxmlElement("w:rPr")
    rFonts = OxmlElement("w:rFonts")
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia"):
        rFonts.set(qn(attr), font)
    rPr.append(rFonts)
    half_pts = str(round(size_pt * 2))
    for tag in ("w:sz", "w:szCs"):
        el = OxmlElement(tag)
        el.set(qn("w:val"), half_pts)
        rPr.append(el)
    return rPr


def _get_sectPr(doc: Document):
    body = doc.element.body
    sectPr = body.find(qn("w:sectPr"))
    if sectPr is None:
        sectPr = OxmlElement("w:sectPr")
        body.append(sectPr)
    return sectPr


def _get_or_create(parent, prefixed: str):
    el = parent.find(qn(prefixed))
    if el is None:
        el = OxmlElement(prefixed)
        parent.append(el)
    return el
