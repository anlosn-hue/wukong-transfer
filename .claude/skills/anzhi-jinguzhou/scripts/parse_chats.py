# -*- coding: utf-8 -*-
"""紧箍咒 Step 1 机械解析：企微会话导出 xlsx -> 结构化文本。

用法: python parse_chats.py <xlsx路径> <输出目录>
产出: <输出目录>/01-解析.txt（UTF-8）
stdout: JSON 统计（会话数/消息数/未解析片段等），供悟空核对

只做机械拆分（按行拆会话、按 @@@ 拆消息、拆发言人/时间/内容），
不做角色判定与规则判定——那是语义层，由悟空按 SKILL.md Step 2-4 完成。
数据形态约定见 spec 第二节：一行=一段会话，仅 A 列有效；
消息格式「发言人 HH:MM:SS：  内容」；发言人可含空格（如 昵称含 emoji+空格）。
"""
import sys
import re
import io
import json
from pathlib import Path

import pandas as pd

# 发言人非贪婪匹配到第一个「空格+时分秒+全角冒号」为止；内容可跨行（re.S）
# 时间戳容忍脱敏残缺（如 :48:01 / 11::27 / 15:43:）：2-8 位数字与冒号组合，
# 顺序以 @@@ 分段为准，时间本身不参与判定（2026-07-24 脱敏样例驱动放宽）
MSG_RE = re.compile(
    r'^(?P<speaker>.+?)\s+(?P<time>[\d:]{2,8})：\s*(?P<content>.*)$', re.S)


def say(msg: str):
    """UTF-8 安全输出，避免 GBK 控制台下报错提示自身抛 UnicodeEncodeError。"""
    sys.stdout.buffer.write((msg + '\n').encode('utf-8'))


def parse_row(text: str):
    """一段会话文本 -> (消息列表, 未解析片段列表)"""
    segments = [s.strip() for s in text.split('@@@') if s.strip()]
    messages, bad = [], []
    for seg in segments:
        m = MSG_RE.match(seg)
        if m:
            messages.append({
                'speaker': m.group('speaker').strip(),
                'time': m.group('time'),
                'content': m.group('content').strip(),
            })
        else:
            bad.append(seg)
    return messages, bad


def main():
    if len(sys.argv) != 3:
        say('用法: python parse_chats.py <xlsx路径> <输出目录>')
        sys.exit(2)
    xlsx, outdir = Path(sys.argv[1]), Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    try:
        df = pd.read_excel(xlsx, sheet_name='Sheet1', header=None, dtype=str)
    except Exception as e:
        say(f'格式异常：读不到 Sheet1（{e}），停止。请报告用户。')
        sys.exit(1)
    if df.empty:
        say('格式异常：Sheet1 为空，停止。请报告用户。')
        sys.exit(1)

    out = io.StringIO()
    stats = {
        '会话数': 0,
        '消息数': 0,
        '未解析片段数': 0,
        '跳过空行数': 0,
        '表头异常': False,
        '未解析片段': [],
    }
    for i, row in df.iterrows():
        excel_row = i + 1          # 与 Excel 行号一致（1-based），行号是全流程主键
        cell = row[0]
        if excel_row == 1:
            header_text = '' if pd.isna(cell) else str(cell).strip()
            if header_text == '聊天内容':
                continue            # 表头行「聊天内容」，跳过
            # 表头缺失/改样——不静默吞掉，按普通会话行往下解析，标记待人工复核
            stats['表头异常'] = True
        if pd.isna(cell) or not str(cell).strip():
            stats['跳过空行数'] += 1
            continue
        messages, bad = parse_row(str(cell))
        stats['会话数'] += 1
        stats['消息数'] += len(messages)
        stats['未解析片段数'] += len(bad)
        for b in bad:
            stats['未解析片段'].append({'行': excel_row, '片段前80字': b[:80]})
        out.write(f'===== 行{excel_row} =====\n')
        for n, msg in enumerate(messages, 1):
            out.write(f"[{n}] {msg['speaker']} {msg['time']} | {msg['content']}\n")
        for b in bad:
            out.write(f'[未解析] {b}\n')
        out.write('\n')

    if stats['会话数'] == 0:
        say('格式异常：0个会话被解析，可能数据不在A列或格式有变，停止。请报告用户。')
        sys.exit(1)

    (outdir / '01-解析.txt').write_text(out.getvalue(), encoding='utf-8')
    sys.stdout.buffer.write(
        json.dumps(stats, ensure_ascii=False, indent=2).encode('utf-8'))


if __name__ == '__main__':
    main()
