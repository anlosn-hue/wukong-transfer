# -*- coding: utf-8 -*-
"""读 config.yaml；路径.登录态目录/台账文件为相对技能目录，解析为绝对路径。"""
from pathlib import Path
import yaml

SKILL_DIR = Path(__file__).resolve().parents[1]

def load_config() -> dict:
    cfg = yaml.safe_load((SKILL_DIR / "config.yaml").read_text(encoding="utf-8"))
    路径 = cfg["路径"]
    路径["登录态目录_绝对"] = str(SKILL_DIR / 路径["登录态目录"])
    路径["台账文件_绝对"] = str(SKILL_DIR / 路径["台账文件"])
    return cfg
