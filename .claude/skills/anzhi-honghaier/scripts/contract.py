# -*- coding: utf-8 -*-
"""红孩儿数据契约：三层漏斗共用的数据 schema + JSON 序列化。"""
from dataclasses import dataclass, field, asdict
from typing import List

@dataclass
class Note:
    """A 层笔记清单条目。"""
    id: str
    标题: str
    作者: str
    发布时间: str
    点赞: int
    收藏: int
    评论: int
    链接: str
    命中筛选: bool = False
    筛选原因: List[str] = field(default_factory=list)

def notes_to_json(notes: List[Note]) -> dict:
    return {"笔记": [asdict(n) for n in notes]}

def notes_from_json(data: dict) -> List[Note]:
    return [Note(**d) for d in data.get("笔记", [])]
