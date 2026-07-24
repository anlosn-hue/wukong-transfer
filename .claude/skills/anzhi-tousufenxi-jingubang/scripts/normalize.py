# -*- coding: utf-8 -*-
"""归一化：原始 xlsx → 标准 CSV 底库。用法：python normalize.py <数据区路径>"""
import json, re, sys
from pathlib import Path
import pandas as pd
import yaml

HEADER_MAP = {"业务细分一级菜单": "一级菜单", "业务细分二级菜单": "二级菜单",
              "业务细分三级菜单": "三级菜单", "主办机构处理结果": "处理结果",
              "主办机构": "主办单位",  # 部分年份sheet用"主办机构"指代同一列
              "意见来源二级菜单": "意见来源"}  # 部分年份sheet带层级后缀
DUBAN_OUT = ["受理时间","主办单位","部门","意见来源","一级菜单","二级菜单","三级菜单",
             "问题点","客户反馈内容","处理结果","是否超时办结","超时天数","超时状态"]
TOUSU_OUT = ["受理日期","责任机构","一级菜单","二级菜单","三级菜单","问题点",
             "客户反馈内容","处理结果","意见来源"]

def detect_type(headers):
    # 用"是否超时办结"/"责任机构"这两个跨年份稳定不变的列判型，
    # 不依赖"受理时间"vs"受理日期"这类会随年份漂移的列名（2026-07-08发现去年6月sheet用词不同）
    hs = {str(h).strip() for h in headers}
    if "是否超时办结" in hs:
        return "duban"
    if "责任机构" in hs:
        return "tousu"
    return None

def detect_month(sheet_name, file_name, df):
    for text in (sheet_name, file_name):
        m = re.search(r"(\d{4})\s*[年\-/.]\s*(\d{1,2})", str(text))
        if m:
            return f"{m.group(1)}-{int(m.group(2)):02d}"
    col = "受理时间" if "受理时间" in df.columns else "受理日期"
    dt = pd.to_datetime(df[col], errors="coerce").dropna()
    if len(dt):
        return dt.dt.strftime("%Y-%m").mode().iloc[0]
    return None

def load_dept_map(path):
    p = Path(path)
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}

def _overtime_status(row):
    """超时口径（2026-07-21 用户定）：只认「超时天数」≥1 天，不看「是否超时办结」标志位——
    真实数据里 2026 年 5-6 月 3034 行仅 2 行填「是」，而带超时天数的有 380 行，标志位不可用。
    （原口径 =是→已办结超时／空且天数>0→在办超时／=否→正常，已废止）"""
    days = row.get("超时天数")
    return "超时" if pd.notna(days) and days >= 1 else "正常"

def clean(df, kind, dept_map):
    df = df.rename(columns=HEADER_MAP).copy()
    if kind == "tousu" and "受理日期" not in df.columns and "受理时间" in df.columns:
        df = df.rename(columns={"受理时间": "受理日期"})  # 老sheet列名漂移
    # 历史 sheet 字段存在差异，缺列时补空，避免一次字段漂移阻断整批入库
    if kind == "tousu":
        for col in TOUSU_OUT:
            if col not in df.columns:
                df[col] = ""
    else:
        for col in DUBAN_OUT:
            if col not in df.columns:
                df[col] = ""
    for c in df.columns:
        # 全角空格归一 + 去首尾空白；同时把 | 和换行转掉——这些字符若混进"问题点"等字段会撞坏
        # render_report.py/m08_activity.py 的markdown表格逐行split("|")解析（代码审查2026-07-07发现）
        df[c] = (df[c].where(df[c].notna(), "").astype(str).str.replace("　", " ")
                 .str.replace("|", "｜").str.replace("\r\n", " ").str.replace("\n", " ").str.strip())
    二, 三 = df["二级菜单"].fillna(""), df["三级菜单"].fillna("")
    # 菜单层级之间用「-」连接，不用「/」——菜单名本身常含「/」（如"短信未达/延迟问题"），
    # 用「/」当连接符会让读者分不清哪个斜杠是层级分隔（2026-07-21 用户要求）
    df["问题点"] = [f"{a}-{b}" if b else a for a, b in zip(二, 三)]
    unmapped = []
    if kind == "duban":
        df["超时天数"] = pd.to_numeric(df["超时天数"], errors="coerce")
        df["超时状态"] = df.apply(_overtime_status, axis=1)
        def _map(u):
            if u in dept_map:
                return dept_map[u]
            if u and u not in unmapped:
                unmapped.append(u)
            return "未映射"
        df["部门"] = df["主办单位"].map(_map)
        return df[DUBAN_OUT], unmapped
    return df[TOUSU_OUT], unmapped

def run(base):
    base = Path(base)
    raw, lib = base / "原始", base / "底库"
    (lib / "duban").mkdir(parents=True, exist_ok=True)
    (lib / "tousu").mkdir(parents=True, exist_ok=True)
    dept_map = load_dept_map(lib / "部门映射.yaml")
    summary = {"入库": [], "未识别": [], "未映射主办单位": []}
    meta_p = lib / "_meta.json"
    meta = json.loads(meta_p.read_text(encoding="utf-8")) if meta_p.exists() else {"duban": {}, "tousu": {}}
    buckets = {}  # (kind, month) -> [DataFrame,...]；同月数据可能来自不同sheet/文件，需合并
    for f in sorted(raw.glob("*.xlsx")):
        if f.name.startswith("~$"):
            continue
        for sheet, df in pd.read_excel(f, sheet_name=None, dtype=str).items():
            df.columns = [str(c).strip() for c in df.columns]  # 去列名首尾空格（如" 意见来源"）
            kind = detect_type(df.columns)
            if kind is None:
                summary["未识别"].append(f"{f.name}::{sheet}")
                continue
            out, unmapped = clean(df, kind, dept_map)
            summary["未映射主办单位"] += [u for u in unmapped if u not in summary["未映射主办单位"]]
            # 按行内实际受理日期拆月——同一sheet可能横跨多个月（如"2026年5月、6月"合并表），
            # 不能只按sheet名/文件名打一个整体月份标签（2026-07-08真实数据发现此问题）
            date_col = "受理时间" if kind == "duban" else "受理日期"
            row_month = pd.to_datetime(out[date_col], errors="coerce").dt.strftime("%Y-%m")
            if row_month.isna().all():
                fallback = detect_month(sheet, f.name, out)
                if fallback is None:
                    summary["未识别"].append(f"{f.name}::{sheet}（月份不明）")
                    continue
                row_month = pd.Series(fallback, index=out.index)
            elif row_month.isna().any():
                bad = int(row_month.isna().sum())
                summary["未识别"].append(f"{f.name}::{sheet}（{bad}行日期无法解析，已跳过）")
            for month, grp in out.groupby(row_month):
                buckets.setdefault((kind, month), []).append(grp)
    for (kind, month), parts in buckets.items():
        combined = pd.concat(parts, ignore_index=True)
        combined.to_csv(lib / kind / f"{month}.csv", index=False, encoding="utf-8-sig")
        summary["入库"].append({"表": kind, "月份": month, "条数": len(combined)})
        meta[kind][month] = {"条数": len(combined)}
    meta["未映射主办单位"] = summary["未映射主办单位"]  # 持久化，供 INDEX 全貌页"映射待补"板块渲染
    meta_p.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return summary

if __name__ == "__main__":
    print(json.dumps(run(sys.argv[1]), ensure_ascii=False, indent=1))
