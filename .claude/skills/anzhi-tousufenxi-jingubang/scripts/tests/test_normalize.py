# -*- coding: utf-8 -*-
import json
import pandas as pd
import normalize

def test_detect_type_by_header():
    assert normalize.detect_type(["受理时间","主办单位","是否超时办结"]) == "duban"
    assert normalize.detect_type(["受理日期","责任机构","意见来源"]) == "tousu"
    assert normalize.detect_type(["无关","表头"]) is None

def test_detect_month_from_sheet_name():
    df = pd.DataFrame({"受理时间": ["2026-05-01 10:00:00"]})
    assert normalize.detect_month("2026年5月（督办）", "x.xlsx", df) == "2026-05"

def test_detect_month_fallback_to_data():
    df = pd.DataFrame({"受理日期": ["2026-06-03", "2026-06-04", "2026-06-05"]})
    assert normalize.detect_month("Sheet1", "数据.xlsx", df) == "2026-06"

def test_detect_month_sheet_name_takes_priority_over_conflicting_data():
    # 表名说5月，但数据列全是6月——必须以表名为准，证明真的是"表名优先"而不是巧合殊途同归
    df = pd.DataFrame({"受理时间": ["2026-06-01 10:00:00", "2026-06-02 10:00:00"]})
    assert normalize.detect_month("2026年5月（督办）", "x.xlsx", df) == "2026-05"

def test_clean_derives_problem_point_and_overtime(dept_map_file):
    df = pd.DataFrame([
        ["2026-05-01 10:00","兴业银行总行数字运营部","95561","数字运营部","短信问题","短信屏蔽","内容","结果","是","3"],
        ["2026-05-02 11:00","兴业银行总行数字运营部","95561","数字运营部","短信问题","","内容","","","57"],
        ["2026-05-03 12:00","未知新单位","95561","数字运营部","短信问题","短信屏蔽","内容","结果","否","5"],
    ], columns=["受理时间","主办单位","意见来源","业务细分一级菜单","业务细分二级菜单",
                "业务细分三级菜单","客户反馈内容","主办机构处理结果","是否超时办结","超时天数"])
    dept_map = normalize.load_dept_map(dept_map_file / "部门映射.yaml")
    out, unmapped = normalize.clean(df, "duban", dept_map)
    assert out["问题点"].tolist() == ["短信问题-短信屏蔽", "短信问题", "短信问题-短信屏蔽"]
    # 口径（用户2026-07-21改定）：只认超时天数≥1，不看「是否超时办结」标志位
    # （第3行标志位为"否"但天数5天，旧口径判正常、新口径判超时）
    assert out["超时状态"].tolist() == ["超时", "超时", "超时"]
    assert out["部门"].tolist() == ["数字运营部", "数字运营部", "未映射"]
    assert unmapped == ["未知新单位"]

def test_clean_sanitizes_pipe_and_newline(dept_map_file):
    # 代码审查发现：字段里的字面量"|"或换行会撞坏render_report.py/m08_activity.py的markdown表格逐行解析
    df = pd.DataFrame([
        ["2026-05-01 10:00","兴业银行总行数字运营部","95561","数字运营部","短信|问题","屏蔽\n换行",
         "内容里有|竖线\n和换行","结果","否","5"],
    ], columns=["受理时间","主办单位","意见来源","业务细分一级菜单","业务细分二级菜单",
                "业务细分三级菜单","客户反馈内容","主办机构处理结果","是否超时办结","超时天数"])
    dept_map = normalize.load_dept_map(dept_map_file / "部门映射.yaml")
    out, _ = normalize.clean(df, "duban", dept_map)
    assert "|" not in out["问题点"].iloc[0] and "\n" not in out["问题点"].iloc[0]
    assert "|" not in out["客户反馈内容"].iloc[0] and "\n" not in out["客户反馈内容"].iloc[0]

def test_clean_handles_real_excel_roundtrip_whitespace_and_blank_cells(dept_map_file, tmp_path):
    """真实场景回归测试：pandas 3.0下 read_excel(dtype=str) 返回的是新string dtype而非object，
    此前 clean() 的 dtype==object 判断因此失效——空白格是真NaN、单位名可能带前后空格/全角空格。
    这条测试用真实Excel I/O（不是手搭DataFrame）复现，验证清洗真的生效。"""
    import openpyxl
    f = tmp_path / "raw.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    headers = ["受理时间","主办单位","意见来源","业务细分一级菜单","业务细分二级菜单",
               "业务细分三级菜单","客户反馈内容","主办机构处理结果","是否超时办结","超时天数"]
    ws.append(headers)
    ws.append(["2026-05-01 10:00", " 兴业银行总行数字运营部　", "95561", "数字运营部",
               "短信问题", "短信屏蔽", "内容", "结果", "是", "3"])
    ws.append(["2026-05-02 11:00", "兴业银行总行数字运营部", "95561", "数字运营部",
               "短信问题", None, "内容", None, None, "57"])  # 空白格是真NaN，不是""
    wb.save(f)
    df = pd.read_excel(f, dtype=str)
    dept_map = normalize.load_dept_map(dept_map_file / "部门映射.yaml")
    out, unmapped = normalize.clean(df, "duban", dept_map)
    assert unmapped == []  # 前后空格/全角空格不应导致误判未映射
    assert out["部门"].tolist() == ["数字运营部", "数字运营部"]
    assert out["超时状态"].tolist() == ["超时", "超时"]  # 均有超时天数（3天、57天）

def test_run_writes_csv_idempotent(sample_xlsx, dept_map_file, tmp_path):
    base = tmp_path  # 数据区：含 原始/ 底库/
    summary1 = normalize.run(base)
    summary2 = normalize.run(base)  # 重跑幂等
    duban_csv = base / "底库" / "duban" / "2026-05.csv"
    assert duban_csv.exists()
    df = pd.read_csv(duban_csv, encoding="utf-8-sig")
    assert len(df) == 6 and list(df.columns) == normalize.DUBAN_OUT
    assert (base / "底库" / "tousu" / "2026-05.csv").exists()
    assert summary1["入库"] == summary2["入库"]  # 覆盖式，不翻倍
    meta = json.loads((base / "底库" / "_meta.json").read_text(encoding="utf-8"))
    assert meta["duban"]["2026-05"]["条数"] == 6
    assert meta["未映射主办单位"] == []  # 夹具单位全在映射表内
