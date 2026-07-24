# word_format/config_types.py
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class FontConfig:
    font: str
    size_pt: float


@dataclass
class TableConfig:
    font: str
    size_pt: float
    line_spacing_pt: float


@dataclass
class HeadingConfig:
    level: int
    pattern: str
    font: str
    size_pt: float
    bold: bool


@dataclass
class PageNumberConfig:
    mode: str = "daily"        # "daily" | "official"
    font: str = "仿宋"          # 日常模式字体
    size_pt: float = 12.0       # 日常模式字号
    align: str = "center"       # 日常模式对齐


@dataclass
class PageConfig:
    page_width_cm: float
    page_height_cm: float
    margin_top_cm: float
    margin_bottom_cm: float
    margin_left_cm: float
    margin_right_cm: float
    header_dist_cm: float
    footer_dist_cm: float
    grid_font: str
    grid_font_pt: float
    chars_per_line: int
    line_pitch_pt: float
    page_number: PageNumberConfig = field(default_factory=PageNumberConfig)


@dataclass
class BodyConfig:
    main_title: FontConfig
    sub_title: FontConfig
    headings: list[HeadingConfig]
    body: FontConfig
    table: TableConfig


@dataclass
class FormatConfig:
    schema_version: int
    name: str
    description: str
    page: PageConfig
    body: BodyConfig


@dataclass
class CustomFix:
    source: str   # YAML key "from"（Python 保留字，加载时映射）
    target: str   # YAML key "to"


@dataclass
class LeaderConfig:
    name: str
    title: str
    rank: int


@dataclass
class OrgConfig:
    full: str
    abbr: str


@dataclass
class TextCheckConfig:
    fix_date_padding: bool = True
    fix_bullet_chars: bool = True
    fix_zhizhi: bool = True
    fix_quotes: bool = True
    fix_quote_direction: bool = True
    fix_list: bool = True
    custom_fixes: list[CustomFix] = field(default_factory=list)
    leader_check_enabled: bool = False
    ai_typo_check: bool = False
    leaders: list[LeaderConfig] = field(default_factory=list)
    org_check_enabled: bool = False
    orgs: list[OrgConfig] = field(default_factory=list)
