# -*- coding: utf-8 -*-
import sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from contract import Note
from funnel import 筛选A层, 解析日期

风险词 = ["未到账", "投诉", "套路"]
阈值 = {"点赞": 50, "收藏": 20, "评论": 5}
今 = date(2026, 7, 11)

def _n(**kw):
    base = dict(id="i", 标题="标题", 作者="a", 发布时间="2026-07-10",
                点赞=0, 收藏=0, 评论=0, 链接="u")
    base.update(kw)
    return Note(**base)

def test_hit_by_risk_word_in_title():
    notes = [_n(标题="活动奖励未到账怎么办")]
    out = 筛选A层(notes, 风险语气词=风险词, 互动阈值=阈值)
    assert out[0].命中筛选 is True
    assert any("风险词" in r for r in out[0].筛选原因)

def test_hit_by_interaction():
    notes = [_n(标题="普通分享", 点赞=100)]
    out = 筛选A层(notes, 风险语气词=风险词, 互动阈值=阈值)
    assert out[0].命中筛选 is True
    assert any("互动" in r for r in out[0].筛选原因)

def test_miss_when_neither():
    notes = [_n(标题="今天天气不错", 点赞=3, 收藏=1, 评论=0)]
    out = 筛选A层(notes, 风险语气词=风险词, 互动阈值=阈值)
    assert out[0].命中筛选 is False
    assert out[0].筛选原因 == []

# —— 时间窗降级兜底（尽力+不误杀）——
def test_解析日期_多格式():
    assert 解析日期("2026-07-10", 今) == date(2026, 7, 10)
    assert 解析日期("07-10", 今) == date(2026, 7, 10)
    assert 解析日期("3天前", 今) == date(2026, 7, 8)
    assert 解析日期("昨天", 今) == date(2026, 7, 10)
    assert 解析日期("", 今) is None          # 解析不到
    assert 解析日期("前段时间", 今) is None

def test_时间窗_滤除窗外可解析老帖():
    notes = [_n(标题="活动未到账", 发布时间="2026-06-01", 点赞=99)]  # 命中风险+互动，但40天前
    out = 筛选A层(notes, 风险语气词=风险词, 互动阈值=阈值, 时间窗天数=30, 今日=今)
    assert out[0].命中筛选 is False
    assert any("时间窗外" in r for r in out[0].筛选原因)

def test_时间窗_保留窗内():
    notes = [_n(标题="活动未到账", 发布时间="2026-07-05", 点赞=99)]
    out = 筛选A层(notes, 风险语气词=风险词, 互动阈值=阈值, 时间窗天数=30, 今日=今)
    assert out[0].命中筛选 is True

def test_时间窗_日期未知不误杀():
    notes = [_n(标题="活动未到账", 发布时间="", 点赞=99)]  # 解析不到日期 → 保留
    out = 筛选A层(notes, 风险语气词=风险词, 互动阈值=阈值, 时间窗天数=30, 今日=今)
    assert out[0].命中筛选 is True
