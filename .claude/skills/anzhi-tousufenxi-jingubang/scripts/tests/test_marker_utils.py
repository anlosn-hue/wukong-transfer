# -*- coding: utf-8 -*-
"""脚注标记 〔fn:KEY〕 与悬浮标记 〔tip:标签¦明细〕 的解析。

悬浮标记只在 HTML 有交互形态；docx/md 必须自动退化为纯标签文字，
否则正式公文里会漏出「〔tip:...〕」这种源码。
"""
import marker_utils as mu


# ---------- 〔fn:KEY〕 ----------

def test_split_markers_基本():
    assert mu.split_markers("甲〔fn:k1〕乙") == [("甲", "k1"), ("乙", None)]


def test_strip_markers_去掉全部标记():
    assert mu.strip_markers("甲〔fn:k1〕乙〔fn:k2〕") == "甲乙"


def test_未闭合标记不吞正文():
    assert mu.strip_markers("甲〔fn:k1乙") == "甲〔fn:k1乙"


def test_footnotes_重复key只编一次号():
    tf = mu.TextFootnotes({"k": "注文"})
    assert tf.sub("A〔fn:k〕B〔fn:k〕", lambda n, k: f"[{n}]") == "A[1]B"
    assert tf.order == [(1, "k", "注文")]


# ---------- 〔tip:标签¦明细〕 ----------

def test_split_tips_基本():
    assert mu.split_tips("前〔tip:监管49案¦06-07 零售信贷部〕后") == [
        ("前", ("监管49案", "06-07 零售信贷部")), ("后", None)]


def test_strip_tips_退化为标签文字():
    """docx/md 走这条路：只留标签，明细丢弃（明细在附件里）。"""
    assert mu.strip_tips("共〔tip:4案¦甲；乙〕，详见附件") == "共4案，详见附件"


def test_strip_tips_不影响无标记文本():
    assert mu.strip_tips("普通句子。") == "普通句子。"


def test_未闭合tip不吞正文():
    assert mu.strip_tips("甲〔tip:标签¦明细乙") == "甲〔tip:标签¦明细乙"


def test_缺分隔符的tip按空明细处理():
    assert mu.strip_tips("甲〔tip:标签〕乙") == "甲标签乙"


def test_sub_tips_自定义渲染():
    out = mu.sub_tips("〔tip:L¦B〕", lambda label, body: f"<x>{label}|{body}</x>")
    assert out == "<x>L|B</x>"


def test_fn与tip互不干扰():
    s = "甲〔fn:k〕乙〔tip:L¦B〕丙"
    assert mu.strip_tips(mu.strip_markers(s)) == "甲乙L丙"
