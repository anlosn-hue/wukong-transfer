# -*- coding: utf-8 -*-
"""matplotlib 图表生成：条形图/折线图，统一输出 PNG bytes。
docx 原生嵌图、html 转 base64 内嵌，两份产出图表视觉一致（取代 chart_svg.py 的 SVG 方案）。"""
import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

BLUE = "#1a4d8f"
COLORS = ["#1a4d8f", "#d97706", "#2a9d5c", "#a3231b"]

def bar_chart_png(labels, series, title, colors=None, xlabel=None):
    """水平条形图。series: {"系列名": [数值,...]}，支持1个或多个系列（并排分组对比）。
    每根条形末端标注具体数值，避免只看坐标轴看不出量级；xlabel 用于标注数值单位（如"笔"/"超时办结率(%)"）。
    labels 或 series 任一为空时返回 b""（无数据不画图）。"""
    if not labels or not series:
        return b""
    colors = colors or COLORS
    n = len(series)
    fig, ax = plt.subplots(figsize=(7, max(2.5, 0.5 * len(labels))))
    try:
        bar_h = 0.8 / n
        y = list(range(len(labels)))
        maxv = max((v for values in series.values() for v in values), default=0)
        for i, (name, values) in enumerate(series.items()):
            # 组内并排：总宽0.8按系列数均分，各系列居中对齐到y刻度
            offset = (i - (n - 1) / 2) * bar_h
            ys = [yy + offset for yy in y]
            ax.barh(ys, values, height=bar_h, label=name, color=colors[i % len(colors)])
            for yy, v in zip(ys, values):
                ax.annotate(str(v), (v, yy), textcoords="offset points",
                            xytext=(4, 0), va="center", fontsize=8)
        ax.set_yticks(y)
        ax.set_yticklabels(labels)
        ax.invert_yaxis()
        ax.set_xlim(right=maxv * 1.15 if maxv else 1)  # 给数值标注留右侧空间，避免超出画布被裁掉
        ax.set_title(title)
        if xlabel:
            ax.set_xlabel(xlabel)
        if n > 1:
            ax.legend()
        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150)
        return buf.getvalue()
    finally:
        plt.close(fig)

def line_chart_png(series, title, color=BLUE):
    """折线图。series: {"2026-06": 数值,...}，键须已按时间顺序排好（调用方保证）。
    空序列返回 b""。"""
    if not series:
        return b""
    labels, values = list(series.keys()), list(series.values())
    fig, ax = plt.subplots(figsize=(6, 3))
    try:
        ax.plot(labels, values, marker="o", color=color, linewidth=2)
        for x, v in zip(labels, values):
            ax.annotate(str(v), (x, v), textcoords="offset points", xytext=(0, 8), ha="center")
        ax.set_title(title)
        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150)
        return buf.getvalue()
    finally:
        plt.close(fig)
