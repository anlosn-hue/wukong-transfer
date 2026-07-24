# -*- coding: utf-8 -*-
import json
import pandas as pd
import pytest
import run_analysis
from conftest import duban_rows, tousu_rows, DUBAN_HEADERS, TOUSU_HEADERS
from conftest import minimal_config

def test_pipeline_skips_disabled_and_outputs_metrics_json(lib_two_months, tmp_path):
    cfg = minimal_config(lib_two_months)
    out = tmp_path / "报告" / "2026-06"
    result = run_analysis.run(lib_two_months / "底库", "2026-06", cfg, out)
    assert (out / "指标.json").exists()
    data = json.loads((out / "指标.json").read_text(encoding="utf-8"))
    assert data["月份"] == "2026-06"
    assert data["参数快照"]["分析模型"]["排名分析"]["启用"] is False
    assert data["模型"] == {} and data["预警汇总"] == []

def test_warning_sort_red_first():
    ws = [{"级别": "黄"}, {"级别": "红"}, {"级别": "橙"}]
    assert [w["级别"] for w in run_analysis.sort_warnings(ws)] == ["红", "橙", "黄"]

def test_estimate_dig_candidates_dedup_keeps_highest_severity(lib_two_months):
    # 同一问题点被两个模型分别命中（橙+红）——去重后只留一条，且保留更高严重级别
    ctx = {"month": "2026-06",
           "duban": {m: pd.read_csv(lib_two_months / "底库" / "duban" / f"{m}.csv", encoding="utf-8-sig")
                     for m in ("2026-05", "2026-06")},
           "tousu": {m: pd.read_csv(lib_two_months / "底库" / "tousu" / f"{m}.csv", encoding="utf-8-sig")
                     for m in ("2026-05", "2026-06")}}
    p = "协商还款问题-逾期无力归还"  # tousu_rows 默认问题点，2026-06 共12条
    warnings = run_analysis.sort_warnings([
        {"级别": "橙", "问题点": p, "来源模型": "排名分析"},
        {"级别": "红", "问题点": p, "来源模型": "督办投诉比照"},
    ])
    cands = run_analysis.estimate_dig_candidates(ctx, warnings, {"深挖预警级别": ["红", "橙"]})
    assert len(cands) == 1
    assert cands[0]["级别"] == "红"
    assert cands[0]["条数"] == 12  # 督办侧本月问题点是短信问题-短信屏蔽，不命中，只算投诉侧12条
