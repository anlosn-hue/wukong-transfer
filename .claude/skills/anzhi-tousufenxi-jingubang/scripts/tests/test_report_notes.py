# -*- coding: utf-8 -*-
"""「报告说明」章与脚注的体例约束（2026-07-25 新建）。

此前 build_intro 完全没有测试覆盖——整节删除都不会有任何测试失败。
本文件把 knowledge/tools/报告体例规范.md 里对该章的硬约束钉成断言。
"""
import report_notes

METRICS = {
    "月份": "2026-06",
    "数据范围": {"督办": {"条数": 1696, "机构": ["总行数字运营部", "总行零售金融部"]},
                 "投诉": {"条数": 3797, "机构": ["总行数字运营部"]}},
    "菜单归一": ["借记卡增值服务积点权益问题 → 借记卡增值权益服务问题"],
    "参数快照": {"分析模型": {"排名分析": {"启用": True, "TopN": 10},
                              "督办投诉比照": {"启用": True, "回看月数": 3,
                                               "月均笔数": 20, "命中门槛": 10}},
                 "深挖": {"单诉点抽样上限条数": 150, "深挖预警级别": ["红", "橙"]}},
}

def _intro():
    return report_notes.build_intro(METRICS)["table_md"]

def test_intro_has_no_internal_level_codes():
    """规范 A1：L1/L2/L3 等内部方法论代号不得进交付件。"""
    md = _intro()
    for code in ("L1", "L2", "L3", "分析层级"):
        assert code not in md, f"内部术语「{code}」泄漏进报告说明章"

def test_intro_merges_model_list_into_warning_rules():
    """用户 2026-07-25 定（规范 B1a）：模型清单并入预警规则节，不单列一节。"""
    md = _intro()
    assert "### （二）预警级别认定规则与分析模型" in md
    assert "### （三）" not in md and "### （四）" not in md
    assert "督办投诉比照" in md  # 模型表确实还在，只是并了表

def test_intro_drops_self_describing_preamble():
    """规范 B4：删铺垫式元话语，不解释报告自身怎么统计。"""
    md = _intro()
    for phrase in ("本报告分析", "两张表口径不同", "各自独立统计",
                   "本期启用的模型如下", "同一份数据分三个层级"):
        assert phrase not in md, f"元话语「{phrase}」未清除"

def test_intro_discloses_menu_normalization():
    """规范 A8a：跨表菜单归一必须披露，否则读者按诉点名回源表会查不到。"""
    md = _intro()
    assert "借记卡增值服务积点权益问题 → 借记卡增值权益服务问题" in md

def test_intro_omits_menu_disclosure_when_nothing_normalized():
    m = dict(METRICS, 菜单归一=[])
    assert "统一，以保证跨表比照有效" not in report_notes.build_intro(m)["table_md"]

def test_intro_uses_inhouse_table_definitions():
    """规范 A7：督办/投诉的定义用行内口径（是否命中投诉关键词），不按字面推断。"""
    md = _intro()
    assert "未命中投诉关键词" in md and "已命中投诉关键词" in md
    assert "投诉单" in md

def test_intro_says_full_channel_source():
    assert "数据来源为客服全渠道" in _intro()

def test_yellow_rule_states_baseline_is_last_month():
    """批注 1：「首次进入 Top10」基准不明。实现是与日历上月榜比对，措辞须写明。"""
    stds = {r[1] + r[0]: r[2] for r in report_notes.warn_rules(METRICS)}
    assert "较上月新进入 Top10" in stds["排名分析黄"]
    assert "首次进入" not in stds["排名分析黄"]

def test_dig_footnote_keeps_sampling_rule_without_level_code():
    """删 L2 代号（A1）的同时必须保住抽样规则——否则读者无从判断深挖覆盖了多少条。"""
    fn = report_notes.footnotes(METRICS)["深挖"]
    assert "L2" not in fn
    assert "150" in fn and "全量精读" in fn and "随机抽样" in fn

def test_problem_point_footnote_uses_susdian_naming():
    """规范 A5：投诉侧称「诉点」，督办侧称「问题」，不用自造的「问题点」。"""
    fn = report_notes.footnotes(METRICS)["问题点"]
    assert fn.startswith("诉点：") and "督办侧对应位置称「问题」" in fn


# ---- 诉点／问题 分侧称谓（规范 A5）----
# 用户 2026-07-25 定：投诉侧称「诉点」（＝投诉点），督办侧对应位置称「问题」。
# 自造的「问题点」全库废止。展示层字符串是重灾区——它不在 叙述.json 里，
# 只扫 LLM 产出的文本查不到（2026-06 首版即从模型表头漏出 21 处）。

def test_term_by_table_side():
    assert report_notes.term("投诉") == "诉点"
    assert report_notes.term("督办") == "问题"
    assert report_notes.term() == "诉点"  # 缺省按投诉侧

def test_warn_rules_use_susdian():
    for _, _, std, _ in report_notes.warn_rules(METRICS):
        assert "问题点" not in std

def test_model_desc_use_susdian():
    for desc, _, _ in report_notes.MODEL_DESC.values():
        assert "问题点" not in desc

def test_intro_has_no_problem_point_term():
    import re
    assert "问题点" not in re.sub(r"〔fn:[^〕]*〕", "", _intro())  # 〔fn:KEY〕是渲染标记不是正文


# ---- 交付件不得含内部层级代号（规范 A1，全链路把关）----
# 单点修复不够：L1/L2/L3 曾同时藏在 report_notes 脚注、m08 活动章说明、
# render_report 归因摘要标题三处，改一处漏两处。此测试扫全部产出源码里的对客文案。

def test_no_level_codes_in_delivery_strings():
    import re
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    targets = [root / 'report_notes.py', root / 'report_outline.py',
               root / 'render_report.py'] + sorted((root / 'models').glob('m*.py'))
    bad = []
    for p in targets:
        for i, line in enumerate(p.read_text(encoding='utf-8').splitlines(), 1):
            code = line.split('#')[0]            # 注释里允许出现（开发者可读性）
            if '"""' in line or "'''" in line:   # docstring 同理
                continue
            if re.search(r'\bL[123]\b', code):
                bad.append(f'{p.name}:{i}: {line.strip()[:70]}')
    assert not bad, '交付件文案含内部层级代号：\n' + '\n'.join(bad)


def test_footnote_falls_back_to_legacy_sample_key():
    """旧参数快照（2026-07-25 前）键名是「单问题点抽样上限条数」，须仍能取到抽样上限。"""
    legacy = dict(METRICS, 参数快照=dict(METRICS["参数快照"],
                  深挖={"单问题点抽样上限条数": 200, "深挖预警级别": ["红"]}))
    assert "200" in report_notes.footnotes(legacy)["深挖"]

def test_footnote_prefers_new_sample_key():
    assert "150" in report_notes.footnotes(METRICS)["深挖"]
