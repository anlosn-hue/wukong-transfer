# -*- coding: utf-8 -*-
"""第三方数据服务通道（v1 空壳，未采购服务商）。接口就绪，写实现即可挂上。"""
from .base import Channel

class ThirdPartyChannel(Channel):
    def search_notes(self, 关键词, *, 时间窗天数):
        raise NotImplementedError("通道②未接入：第三方数据服务尚未采购/实现，请用 playwright 通道")
    def fetch_detail(self, 笔记):
        raise NotImplementedError("通道②未接入")
    def fetch_comments(self, 笔记):
        raise NotImplementedError("通道②未接入")
