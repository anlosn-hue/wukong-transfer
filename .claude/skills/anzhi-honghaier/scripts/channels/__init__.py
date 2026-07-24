# -*- coding: utf-8 -*-
"""通道工厂：按名字返回通道实例。playwright 通道延迟导入（避免无 playwright 时 import 失败）。"""
from .base import Channel

def get_channel(名字: str) -> Channel:
    if 名字 == "thirdparty":
        from .thirdparty_channel import ThirdPartyChannel
        return ThirdPartyChannel()
    if 名字 == "playwright":
        from .playwright_channel import PlaywrightChannel
        return PlaywrightChannel()
    raise ValueError(f"未知通道: {名字}")
