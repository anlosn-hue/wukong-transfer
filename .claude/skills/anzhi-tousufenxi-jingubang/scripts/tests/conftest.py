# -*- coding: utf-8 -*-
import sys
from pathlib import Path
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # scripts/

DUBAN_HEADERS = ["受理时间","主办单位","意见来源","业务细分一级菜单","业务细分二级菜单",
                 "业务细分三级菜单","客户反馈内容","主办机构处理结果","是否超时办结","超时天数"]
TOUSU_HEADERS = ["受理日期","责任机构","业务细分一级菜单","业务细分二级菜单",
                 "业务细分三级菜单","客户反馈内容","主办机构处理结果","意见来源"]

def duban_rows(n=5, month="2026-05", 二级="短信问题", 三级="短信屏蔽",
               主办="兴业银行总行数字运营部", 超时办结="否", 超时天数=""):
    return [[f"{month}-0{i%9+1} 10:00:00", 主办, "95561", "数字运营部", 二级, 三级,
             f"客户反馈内容样例{i}", f"处理结果样例{i}", 超时办结, 超时天数] for i in range(n)]

def tousu_rows(n=5, month="2026-05", 二级="协商还款问题", 三级="逾期无力归还",
               责任="兴业银行零售信贷部"):
    return [[f"{month}-0{i%9+1}", 责任, "零售信贷部", 二级, 三级,
             f"投诉内容样例{i}", f"处理结果样例{i}", "95561电话"] for i in range(n)]

@pytest.fixture
def sample_xlsx(tmp_path):
    """合成原始文件：一个xlsx含 2026年5月 督办+投诉 两sheet"""
    p = tmp_path / "原始"; p.mkdir()
    f = p / "样例数据.xlsx"
    with pd.ExcelWriter(f, engine="openpyxl") as w:
        pd.DataFrame(duban_rows(6), columns=DUBAN_HEADERS).to_excel(
            w, sheet_name="2026年5月（督办）", index=False)
        pd.DataFrame(tousu_rows(4), columns=TOUSU_HEADERS).to_excel(
            w, sheet_name="2026年5月（投诉）", index=False)
    return p

@pytest.fixture
def dept_map_file(tmp_path):
    p = tmp_path / "底库"; p.mkdir(exist_ok=True)
    (p / "部门映射.yaml").write_text(
        "兴业银行总行数字运营部: 数字运营部\n兴业银行零售信贷部: 零售信贷部\n", encoding="utf-8")
    return p

@pytest.fixture
def lib_two_months(tmp_path, dept_map_file):
    """合成底库：2026-05/06 两月，直接以归一化后CSV形态落盘"""
    import normalize
    base = tmp_path
    (base / "原始").mkdir(exist_ok=True)
    dept_map = normalize.load_dept_map(dept_map_file / "部门映射.yaml")
    for month, dn, tn in [("2026-05", 6, 4), ("2026-06", 9, 12)]:
        d, _ = normalize.clean(pd.DataFrame(duban_rows(dn, month), columns=DUBAN_HEADERS), "duban", dept_map)
        t, _ = normalize.clean(pd.DataFrame(tousu_rows(tn, month), columns=TOUSU_HEADERS), "tousu", dept_map)
        (base / "底库" / "duban").mkdir(parents=True, exist_ok=True)
        (base / "底库" / "tousu").mkdir(parents=True, exist_ok=True)
        d.to_csv(base / "底库" / "duban" / f"{month}.csv", index=False, encoding="utf-8-sig")
        t.to_csv(base / "底库" / "tousu" / f"{month}.csv", index=False, encoding="utf-8-sig")
    return base

def minimal_config(base):
    return {"路径": {"数据区": str(base), "预警点文件": str(base / "预警点.md"),
                    "活动方案库INDEX": str(base / "不存在.md")},
            "分析模型": {"排名分析": {"启用": False}},
            "深挖": {"深挖预警级别": ["红", "橙"], "单批上限字数": 15000,
                    "子代理隔离阈值字数": 50000, "总预算字数": 80000},
            "产出物开关": {}}
