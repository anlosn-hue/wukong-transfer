# -*- coding: utf-8 -*-
import io
import chart_images
from PIL import Image

def test_bar_chart_png_returns_valid_png_single_series():
    png = chart_images.bar_chart_png(
        ["问题点甲", "问题点乙", "问题点丙"],
        {"笔数": [10, 7, 3]},
        "测试排名图")
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    img = Image.open(io.BytesIO(png))
    assert img.width > 100 and img.height > 100

def test_bar_chart_png_supports_grouped_series():
    png = chart_images.bar_chart_png(
        ["甲", "乙"],
        {"投诉笔数": [12, 6], "督办笔数": [3, 1]},
        "分组对比图")
    assert png.startswith(b"\x89PNG\r\n\x1a\n")

def test_bar_chart_png_empty_labels_returns_empty_bytes():
    assert chart_images.bar_chart_png([], {"笔数": []}, "空图") == b""

def test_bar_chart_png_empty_series_dict_with_nonempty_labels_does_not_crash():
    # labels present but series dict empty — must not raise ZeroDivisionError or leak a figure
    png = chart_images.bar_chart_png(["甲", "乙"], {}, "边界情况")
    assert png == b""

def test_line_chart_png_returns_valid_png():
    png = chart_images.line_chart_png({"2026-04": 3, "2026-05": 8, "2026-06": 12}, "测试趋势图")
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    img = Image.open(io.BytesIO(png))
    assert img.width > 100

def test_line_chart_png_empty_series_returns_empty_bytes():
    assert chart_images.line_chart_png({}, "空趋势图") == b""
