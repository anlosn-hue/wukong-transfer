# -*- coding: utf-8 -*-
"""正文标记的解析。三个渲染器（docx/md/html）共用，各自决定怎么落地。

两族标记：
- 〔fn:KEY〕   脚注。docx 落真脚注，md/html 落编号 + 文末注释表。
- 〔tip:标签¦明细〕 悬浮明细。**只有 HTML 有交互形态**（鼠标悬停出蒙版）；
  docx/md 退化为纯标签文字，明细本身另作附件——正式公文不能靠悬停传递信息。
"""

MARK_OPEN, MARK_CLOSE = "〔fn:", "〕"
TIP_OPEN, TIP_CLOSE, TIP_SEP = "〔tip:", "〕", "¦"


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


def split_tips(text):
    """文本 → [(前置文本, (标签, 明细)或None), ...]，最后一项恒为 None。

    缺分隔符时明细为空串（只当作一个高亮标签，不至于整段解析失败）。
    """
    out, rest = [], text or ""
    while TIP_OPEN in rest:
        head, tail = rest.split(TIP_OPEN, 1)
        if TIP_CLOSE not in tail:
            break
        payload, rest = tail.split(TIP_CLOSE, 1)
        label, _, body = payload.partition(TIP_SEP)
        out.append((head, (label.strip(), body.strip())))
    out.append((rest, None))
    return out


def sub_tips(text, fmt):
    """把悬浮标记替换成 fmt(标签, 明细) 的结果。"""
    return "".join(chunk + (fmt(*tip) if tip else "")
                   for chunk, tip in split_tips(text))


def strip_tips(text):
    """退化：只留标签文字，丢弃明细（供 docx/md 等无悬停能力的载体用）。"""
    return sub_tips(text, lambda label, _body: label)


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
