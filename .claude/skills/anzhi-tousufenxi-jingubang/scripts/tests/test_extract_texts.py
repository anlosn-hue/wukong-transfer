# -*- coding: utf-8 -*-
import json
import pandas as pd
import extract_texts

def test_batching_respects_char_limit(lib_two_months, tmp_path):
    out = tmp_path / "batches"
    r = extract_texts.run(lib_two_months / "底库", "2026-06",
                          "协商还款问题-逾期无力归还", out, batch_chars=300, all_months=False)
    assert r["总条数"] == 12
    assert len(r["批次"]) >= 2                       # 300字上限必然切多批
    for b in r["批次"]:
        assert b["字数"] <= 300 + 200                # 单条不截断，允许最后一条溢出
        assert (out / b["文件"]).exists()
    text = (out / r["批次"][0]["文件"]).read_text(encoding="utf-8")
    assert "【反馈】" in text and "【处理】" in text

def test_all_months_flag(lib_two_months, tmp_path):
    r = extract_texts.run(lib_two_months / "底库", "2026-06",
                          "协商还款问题-逾期无力归还", tmp_path / "b2",
                          batch_chars=15000, all_months=True)
    assert r["总条数"] == 16  # 5月4条+6月12条

def test_oversized_single_piece_included_whole_not_truncated(lib_two_months, tmp_path):
    # 代码审查要求补的测试：单条超长文本不能被截断或丢弃，即使远超batch_chars
    p = lib_two_months / "底库" / "tousu" / "2026-06.csv"
    df = pd.read_csv(p, encoding="utf-8-sig")
    long_text = "超长反馈" * 5000  # 2万字
    df.loc[0, "客户反馈内容"] = long_text
    df.to_csv(p, index=False, encoding="utf-8-sig")
    out = tmp_path / "big"
    r = extract_texts.run(lib_two_months / "底库", "2026-06",
                          "协商还款问题-逾期无力归还", out, batch_chars=15000, all_months=False)
    assert max(b["字数"] for b in r["批次"]) > 15000  # 含超长内容的批次必然溢出上限
    all_text = "".join((out / b["文件"]).read_text(encoding="utf-8") for b in r["批次"])
    assert long_text in all_text  # 完整出现，未被截断

def test_missing_feedback_renders_placeholder_not_literal_nan(lib_two_months, tmp_path):
    # 代码审查发现的bug：客户反馈内容为空时，此前会把字面量"nan"写进批次文本喂给LLM
    p = lib_two_months / "底库" / "tousu" / "2026-06.csv"
    df = pd.read_csv(p, encoding="utf-8-sig")
    df.loc[0, "客户反馈内容"] = ""  # 落盘后 read_csv 会重新解析成 NaN，复现真实管线的往返行为
    df.to_csv(p, index=False, encoding="utf-8-sig")
    out = tmp_path / "nan_case"
    r = extract_texts.run(lib_two_months / "底库", "2026-06",
                          "协商还款问题-逾期无力归还", out, batch_chars=15000, all_months=False)
    text = (out / r["批次"][0]["文件"]).read_text(encoding="utf-8")
    assert "【反馈】（空）" in text
    assert "nan" not in text.lower()

def test_rerun_clears_stale_batch_files(lib_two_months, tmp_path):
    # 代码审查发现：同一输出目录重跑，若新批次更少，旧批次文件会残留
    out = tmp_path / "stale"
    extract_texts.run(lib_two_months / "底库", "2026-06",
                      "协商还款问题-逾期无力归还", out, batch_chars=50, all_months=False)
    assert len(list(out.glob("batch_*.txt"))) >= 2  # 小上限先产出多个批次文件
    r2 = extract_texts.run(lib_two_months / "底库", "2026-06",
                           "短信问题-短信屏蔽", out, batch_chars=15000, all_months=False)
    remaining = sorted(p.name for p in out.glob("batch_*.txt"))
    assert remaining == sorted(b["文件"] for b in r2["批次"])  # 不多不少，无残留
