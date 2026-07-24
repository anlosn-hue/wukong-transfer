# word_format/template_loader.py
from __future__ import annotations

import yaml
from pathlib import Path
from typing import NoReturn

from word_format.config_types import (
    FontConfig, TableConfig, HeadingConfig, PageNumberConfig,
    PageConfig, BodyConfig, FormatConfig,
    CustomFix, LeaderConfig, OrgConfig, TextCheckConfig,
)

MODULE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = MODULE_DIR / "templates"
CONFIG_PATH = MODULE_DIR / "config.yaml"
TEXT_CHECK_CONFIG_PATH = MODULE_DIR / "text_check_config.yaml"


def get_default_template_name() -> str:
    cfg = _load_config_yaml()
    return cfg.get("default_template", "公文_本单位")


def set_default_template(name: str) -> None:
    if not (TEMPLATES_DIR / f"{name}.yaml").exists():
        raise FileNotFoundError(f"模板不存在：{name}")
    cfg = _load_config_yaml()
    cfg["default_template"] = name
    cfg.setdefault("schema_version", 1)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False)


def list_templates() -> list[tuple[str, str]]:
    result = []
    for path in sorted(TEMPLATES_DIR.glob("*.yaml")):
        try:
            with open(path, encoding="utf-8") as f:
                d = yaml.safe_load(f) or {}
            result.append((d.get("name", path.stem), d.get("description", "")))
        except Exception:
            result.append((path.stem, ""))
    return result


def load_format_config(name: str | None = None) -> FormatConfig:
    if name is None:
        name = get_default_template_name()
    path = TEMPLATES_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"模板文件不存在：{path}")
    d: dict = {}
    try:
        with open(path, encoding="utf-8") as f:
            d = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        _yaml_error(str(path), exc)
    return _parse_format_config(d, str(path))


def load_text_check_config() -> TextCheckConfig:
    if not TEXT_CHECK_CONFIG_PATH.exists():
        return TextCheckConfig()
    d: dict = {}
    try:
        with open(TEXT_CHECK_CONFIG_PATH, encoding="utf-8") as f:
            d = yaml.safe_load(f) or {}
    except yaml.YAMLError as exc:
        _yaml_error(str(TEXT_CHECK_CONFIG_PATH), exc)
    return _parse_text_check_config(d, str(TEXT_CHECK_CONFIG_PATH))


def _parse_format_config(d: dict, path: str) -> FormatConfig:
    _require(d, "page", path)
    _require(d, "body", path)
    pd = d["page"]
    bd = d["body"]

    pn_d = pd.get("page_number") or {}
    _VALID_MODES = ("daily", "official")
    pn_mode = str(pn_d.get("mode", "daily"))
    if pn_mode not in _VALID_MODES:
        _error(path, f"page_number.mode 取值非法：'{pn_mode}'，合法值为 {_VALID_MODES}")
    page_number = PageNumberConfig(
        mode=pn_mode,
        font=str(pn_d.get("font", "仿宋")),
        size_pt=float(pn_d.get("size_pt", 12.0)),
        align=str(pn_d.get("align", "center")),
    )

    page = PageConfig(
        page_width_cm=float(_req(pd, "page_width_cm", path)),
        page_height_cm=float(_req(pd, "page_height_cm", path)),
        margin_top_cm=float(_req(pd, "margin_top_cm", path)),
        margin_bottom_cm=float(_req(pd, "margin_bottom_cm", path)),
        margin_left_cm=float(_req(pd, "margin_left_cm", path)),
        margin_right_cm=float(_req(pd, "margin_right_cm", path)),
        header_dist_cm=float(_req(pd, "header_dist_cm", path)),
        footer_dist_cm=float(_req(pd, "footer_dist_cm", path)),
        grid_font=str(_req(pd, "grid_font", path)),
        grid_font_pt=float(_req(pd, "grid_font_pt", path)),
        chars_per_line=int(_req(pd, "chars_per_line", path)),
        line_pitch_pt=float(_req(pd, "line_pitch_pt", path)),
        page_number=page_number,
    )

    for key in ("main_title", "sub_title", "body", "table"):
        _require(bd, key, path)

    headings = [
        HeadingConfig(
            level=int(_req(h, "level", path)),
            pattern=str(_req(h, "pattern", path)),
            font=str(_req(h, "font", path)),
            size_pt=float(_req(h, "size_pt", path)),
            bold=bool(h.get("bold", False)),
        )
        for h in (bd.get("headings") or [])
    ]

    body_cfg = BodyConfig(
        main_title=FontConfig(str(_req(bd["main_title"], "font", path)),
                              float(_req(bd["main_title"], "size_pt", path))),
        sub_title=FontConfig(str(_req(bd["sub_title"], "font", path)),
                             float(_req(bd["sub_title"], "size_pt", path))),
        headings=headings,
        body=FontConfig(str(_req(bd["body"], "font", path)),
                        float(_req(bd["body"], "size_pt", path))),
        table=TableConfig(
            font=str(_req(bd["table"], "font", path)),
            size_pt=float(_req(bd["table"], "size_pt", path)),
            line_spacing_pt=float(_req(bd["table"], "line_spacing_pt", path)),
        ),
    )

    return FormatConfig(
        schema_version=int(d.get("schema_version", 1)),
        name=str(d.get("name", "")),
        description=str(d.get("description", "")),
        page=page,
        body=body_cfg,
    )


def _parse_text_check_config(d: dict, path: str) -> TextCheckConfig:
    built_in = d.get("built_in") or {}
    custom_raw = d.get("custom_fixes") or []
    leader_d = d.get("leader_check") or {}
    org_d = d.get("org_check") or {}

    custom_fixes = []
    for item in custom_raw:
        if "from" not in item or "to" not in item:
            _error(path, f"custom_fixes 条目缺少 from 或 to 字段：{item}")
        custom_fixes.append(CustomFix(source=str(item["from"]), target=str(item["to"])))

    leaders = [
        LeaderConfig(
            name=str(_req(ldr, "name", path)),
            title=str(ldr.get("title", "")),
            rank=int(_req(ldr, "rank", path)),
        )
        for ldr in (leader_d.get("leaders") or [])
    ]

    orgs = [
        OrgConfig(
            full=str(_req(org, "full", path)),
            abbr=str(org.get("abbr", "")),
        )
        for org in (org_d.get("orgs") or [])
    ]

    return TextCheckConfig(
        fix_date_padding=bool(built_in.get("fix_date_padding", True)),
        fix_bullet_chars=bool(built_in.get("fix_bullet_chars", True)),
        fix_zhizhi=bool(built_in.get("fix_zhizhi", True)),
        fix_quotes=bool(built_in.get("fix_quotes", True)),
        fix_quote_direction=bool(built_in.get("fix_quote_direction", True)),
        fix_list=bool(built_in.get("fix_list", True)),
        custom_fixes=custom_fixes,
        leader_check_enabled=bool(leader_d.get("enabled", False)),
        ai_typo_check=bool(leader_d.get("ai_typo_check", False)),
        leaders=leaders,
        org_check_enabled=bool(org_d.get("enabled", False)),
        orgs=orgs,
    )


def _load_config_yaml() -> dict:
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {"default_template": "公文_本单位"}
    except yaml.YAMLError as exc:
        _yaml_error(str(CONFIG_PATH), exc)
        raise  # unreachable, satisfies type checker


def _require(d: dict, key: str, path: str) -> None:
    if key not in d:
        _error(path, f"缺少必填字段：{key}")


def _req(d: dict, key: str, path: str):
    if key not in d:
        _error(path, f"缺少必填字段：{key}")
    return d[key]


def _error(path: str, msg: str) -> NoReturn:
    print(f"❌ 配置文件格式错误（{Path(path).name}）\n   {msg}")
    raise SystemExit(1)


def _yaml_error(path: str, exc: yaml.YAMLError) -> NoReturn:
    line = ""
    if hasattr(exc, "problem_mark") and exc.problem_mark:
        line = f" 第 {exc.problem_mark.line + 1} 行"
    if "could not find expected ':'" in str(exc) or "mapping" in str(exc):
        hint = "请检查是否使用了全角冒号（：）或缩进不一致"
    else:
        hint = str(exc)
    print(f"❌ 配置文件格式错误（{Path(path).name}{line}）\n   {hint}")
    raise SystemExit(1)
