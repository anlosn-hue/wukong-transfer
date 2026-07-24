# -*- coding: utf-8 -*-
"""Playwright 通道：自有小号半自动查询小红书。
解析函数（parse_*）纯函数可单测；浏览器驱动（search_notes 等）人工冒烟。
选择器在后续冒烟时按真实页面回填（本文件 + fixture 同步更新）。"""
import re
import random
import time
from pathlib import Path
from typing import List
from bs4 import BeautifulSoup
from .base import Channel
from contract import Note

def _to_int(s: str) -> int:
    """'1.2万' / '120' / '' → int。"""
    s = (s or "").strip()
    if not s:
        return 0
    m = re.match(r"([\d.]+)\s*万", s)
    if m:
        return int(float(m.group(1)) * 10000)
    digits = re.sub(r"[^\d]", "", s)
    return int(digits) if digits else 0

def parse_search_html(html: str, *, 链接前缀: str) -> List[Note]:
    """解析小红书搜索结果页 HTML → Note 列表。
    选择器据 2026-07-11 真实页面回填：卡片 section.note-item；id 取隐藏的
    a[href^="/explore/"]；链接取带 xsec_token 的 a.cover/a.title href；
    标题 a.title；作者 .author .name；时间 .time；点赞 .like-wrapper .count。
    搜索卡不展示收藏/评论数，置 0（进入 B 层后不依赖这两个字段）。"""
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for c in soup.select("section.note-item"):
        exp = c.select_one('a[href^="/explore/"]')
        if not exp or not exp.get("href"):
            continue
        nid = exp["href"].split("/explore/")[1].split("?")[0]
        主链 = c.select_one("a.cover") or c.select_one("a.title")
        href = 主链["href"] if (主链 and 主链.get("href")) else exp["href"]
        title = c.select_one("a.title")
        name = c.select_one(".author .name")
        tm = c.select_one(".time")
        cnt = c.select_one(".like-wrapper .count")
        out.append(Note(
            id=nid,
            标题=title.get_text(strip=True) if title else "",
            作者=name.get_text(strip=True) if name else "",
            发布时间=tm.get_text(strip=True) if tm else "",
            点赞=_to_int(cnt.get_text(strip=True)) if cnt else 0,
            收藏=0, 评论=0,
            链接=(链接前缀 + href) if href.startswith("/") else href,
        ))
    return out

def parse_detail_html(html: str) -> str:
    """解析小红书笔记详情页 → 正文纯文本（标题 + 正文描述）。
    真实结构（2026-07-11 回填）：#detail-title 标题，#detail-desc 正文（含话题标签）。
    兜底：若无这两个 id，退回 .note-content 全文。"""
    soup = BeautifulSoup(html, "html.parser")
    parts = []
    t = soup.select_one("#detail-title")
    if t:
        parts.append(t.get_text(strip=True))
    d = soup.select_one("#detail-desc")
    if d:
        parts.append(d.get_text(" ", strip=True))
    if not parts:
        nc = soup.select_one(".note-content")
        if nc:
            parts.append(nc.get_text(" ", strip=True))
    return "\n".join(parts)

def parse_comments_html(html: str):
    """解析小红书笔记页评论 → 评论文本列表（含主评论与子评论）。
    真实结构（2026-07-11 回填）：.comment-item 内 .content 为评论正文。"""
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for ci in soup.select(".comment-item"):
        con = ci.select_one(".content")
        if con:
            txt = con.get_text(strip=True)
            if txt:
                out.append(txt)
    return out

def state_path(登录态目录: str) -> str:
    return str(Path(登录态目录) / "state.json")

def has_login_state(登录态目录: str) -> bool:
    return Path(state_path(登录态目录)).exists()

def _is_logged_in(ctx) -> bool:
    """用小红书自我信息 API 判定是否**真正登录**（data.guest==False 且有 user_id）。
    注意：访客态也会有 web_session cookie，故不能用 cookie 判登录，必须问 me API。"""
    try:
        r = ctx.request.get("https://edith.xiaohongshu.com/api/sns/web/v2/user/me")
        if r.status != 200:
            return False
        data = r.json().get("data", {})
        return data.get("guest") is False and bool(data.get("user_id"))
    except Exception:
        return False

def ensure_login(登录态目录: str, *, 超时秒: int = 300, 轮询秒: int = 3):
    """无登录态则拉起有头浏览器让用户扫码，**轮询 me API 检测真正登录后自动存 state**（不依赖 input，
    因终端/`!` 执行环境无交互 stdin）；有登录态则直接返回。人工步骤（需用户用专用监测小号扫码）。"""
    from playwright.sync_api import sync_playwright
    Path(登录态目录).mkdir(parents=True, exist_ok=True)
    if has_login_state(登录态目录):
        return
    with sync_playwright() as p:
        b = p.chromium.launch(headless=False)
        ctx = b.new_context()
        page = ctx.new_page()
        page.goto("https://www.xiaohongshu.com", wait_until="domcontentloaded", timeout=60000)
        print(f"请用【专用监测小号】扫码登录小红书；检测到登录后自动保存，无需按回车（最多等 {超时秒} 秒）…")
        截止 = time.time() + 超时秒
        已存 = False
        while time.time() < 截止:
            if _is_logged_in(ctx):
                ctx.storage_state(path=state_path(登录态目录))
                已存 = True
                print("[OK] 检测到登录，登录态已保存：" + state_path(登录态目录))
                break
            time.sleep(轮询秒)
        if not 已存:
            print("[!] 超时未检测到登录，未保存。请重跑本命令再试。")
        b.close()

class BlockedError(RuntimeError):
    """命中平台风控/滑块，视为预期内情形（spec §4.2/§6）。"""

def _is_blocked(page) -> bool:
    """判定是否命中风控/验证页。只看**页面标题**与**可见的**验证组件，
    不做整页 HTML 子串匹配——小红书前端 bundle 恒含 'captcha' 字样（.fe-captcha-app 样式类），
    子串匹配会把正常搜索页误判为风控（2026-07-11 冒烟实测：一页 captcha 出现 52 次全在 CSS）。"""
    try:
        标题 = page.title() or ""
    except Exception:
        标题 = ""
    if any(k in 标题 for k in ["安全限制", "验证码", "滑动验证", "异常访问", "访问异常", "出错了"]):
        return True
    try:
        el = page.locator(".fe-captcha-app, .captcha-container").first
        if el.count() and el.is_visible():
            return True
    except Exception:
        pass
    return False

class PlaywrightChannel(Channel):
    def __init__(self, 登录态目录: str = ".state", 间隔秒=(2, 6), 链接前缀="https://www.xiaohongshu.com"):
        self.登录态目录 = 登录态目录
        self.间隔秒 = 间隔秒
        self.链接前缀 = 链接前缀

    def _sleep(self):
        time.sleep(random.uniform(*self.间隔秒))

    def _new_context(self, p):
        if not has_login_state(self.登录态目录):
            raise RuntimeError("无登录态，请先运行 ensure_login 扫码（专用监测小号）")
        # 有头模式（headless=False）：小红书对无头浏览器检测严、易触发"安全限制"（2026-07-11 冒烟实测）。
        # 有头是最不规避的选择（真实可见浏览器，非反检测手段，契合红孩儿"半自动"定位）。
        b = p.chromium.launch(headless=False)
        return b, b.new_context(storage_state=state_path(self.登录态目录))

    def search_notes(self, 关键词, *, 时间窗天数):
        # 时间窗天数：Playwright 通道不在搜索端过滤（小红书搜索无稳定时间参数），
        # 时间窗由 funnel 兜底过滤；此参数保留给支持服务端时间过滤的第三方通道。
        from urllib.parse import quote
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b, ctx = self._new_context(p)
            page = ctx.new_page()
            # domcontentloaded 而非默认 load：小红书重前端 SPA 的 load 常 30s 不触发致超时。
            # 内容由 JS 异步渲染，故 goto 后再显式等待卡片选择器出现，而非靠固定 sleep（冒烟实测：
            # 只 sleep 会在渲染前抓到空页 → 0 结果）。
            page.goto(f"{self.链接前缀}/search_result?keyword={quote(关键词)}",
                      wait_until="domcontentloaded", timeout=60000)
            self._sleep()
            if _is_blocked(page):
                b.close()
                raise BlockedError("命中风控/滑块页")
            try:
                page.wait_for_selector("section.note-item", timeout=15000)
            except Exception:
                pass   # 可能确实无结果；交给 parse 返回空清单（无命中≠失败）
            html = page.content()
            b.close()
        return parse_search_html(html, 链接前缀=self.链接前缀)

    def fetch_detail(self, 笔记):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b, ctx = self._new_context(p)
            page = ctx.new_page()
            page.goto(笔记.链接, wait_until="domcontentloaded", timeout=60000)
            self._sleep()
            if _is_blocked(page):
                b.close()
                raise BlockedError("命中风控/滑块页")
            try:
                page.wait_for_selector("#detail-desc, .note-content", timeout=15000)
            except Exception:
                pass
            html = page.content()
            b.close()
        return parse_detail_html(html)
    def fetch_comments(self, 笔记):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b, ctx = self._new_context(p)
            page = ctx.new_page()
            page.goto(笔记.链接, wait_until="domcontentloaded", timeout=60000)
            self._sleep()
            if _is_blocked(page):
                b.close()
                raise BlockedError("命中风控/滑块页")
            try:
                page.wait_for_selector(".comment-item", timeout=10000)
            except Exception:
                pass   # 该笔记可能无评论；容忍超时，parse 返回空列表
            html = page.content()
            b.close()
        return parse_comments_html(html)
