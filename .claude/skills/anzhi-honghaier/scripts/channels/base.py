# -*- coding: utf-8 -*-
"""通道抽象接口：漏斗管线只依赖此契约，后端可切换（Playwright / 第三方 API）。"""
from abc import ABC, abstractmethod
from typing import List
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from contract import Note

class Channel(ABC):
    @abstractmethod
    def search_notes(self, 关键词: str, *, 时间窗天数: int) -> List[Note]:
        """A 层：搜关键词返回笔记清单（未筛选）。"""

    @abstractmethod
    def fetch_detail(self, 笔记: Note) -> str:
        """B 层：抓单篇笔记正文纯文本。"""

    @abstractmethod
    def fetch_comments(self, 笔记: Note) -> List[str]:
        """C 层：抓单篇笔记评论文本列表。"""
