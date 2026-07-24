# -*- coding: utf-8 -*-
"""正文脚注标记 〔fn:KEY〕 的解析。三个渲染器（docx/md/html）共用，各自决定怎么落注。"""

MARK_OPEN, MARK_CLOSE = "〔fn:", "〕"


def split_markers(text):
    """文本 → [(前置文本, KEY或None), ...]，最后一项 KEY 恒为 None。"""
    out, rest = [], text or ""
    while MARK_OPEN in rest:
        head, tail = rest.split(MARK_OPEN, 1)
        if MARK_CLOSE not in tail:
            break
        key, rest = tail.split(MARK_CLOSE, 1)
        out.append((head, key.strip()))
    out.append((rest, None))
    return out


def strip_markers(text):
    """去掉全部脚注标记（供不支持脚注的位置用，如表格单元格）。"""
    return "".join(chunk for chunk, _ in split_markers(text))


class TextFootnotes:
    """给 md/html 用的顺序编号器：首次出现的 KEY 分配序号，重复出现不再编号。"""

    def __init__(self, notes):
        self.notes = notes or {}
        self.order = []          # [(序号, KEY, 脚注全文)]
        self._seen = {}

    def sub(self, text, fmt):
        """把标记替换成 fmt(序号, KEY) 的结果；未登记的 KEY 直接去掉标记。"""
        out = []
        for chunk, key in split_markers(text):
            out.append(chunk)
            if key is None:
                continue
            note = self.notes.get(key)
            if not note:
                continue
            if key not in self._seen:
                self._seen[key] = len(self.order) + 1
                self.order.append((self._seen[key], key, note))
                out.append(fmt(self._seen[key], key))
        return "".join(out)
