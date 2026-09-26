#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build.py — 生成《它是怎么动起来的》静态骨架 skeleton.svg

v2 视觉重写。对照样本《Claude by Claude》实测数据后的修正：
  · 色板从 5 色扩到 9 色（样本有 5 档纸灰，靠 opacity 分层）
  · 字号从"大标题+稀疏正文"改成"密集小字 22/24 + 标题 44"（样本 22px 用了 220 次）
  · 加入装饰系统：纸纹噪点 / 斜线网纹 / 半调网点 / 虚线 / 刻度尺 / 进度块 /
    角标 / 伪 UI 标签 / 手绘箭头 / 手绘圈选 / 印章 / 工程图坐标标注
  · 背景层铺满水印词 + 节点网络（样本用大字号低透明度做纸感）

分工不变：叙事性动画 → timeline.json 编译注入；演示性动画 → 这里预写独立短循环。
"""

import math
import random

W, PH, N = 750, 700, 10
H = PH * N

# ---- 色板（样本实测：5 档纸灰 + 2 墨 + 3 灰 + 1 强调） ----
PAPER = "#efe8d8"   # 主纸
PAPER2 = "#f3eee2"  # 浅块
PAPER3 = "#ebe4d4"  # 次级纸
INK = "#1c1b18"     # 主墨
INK2 = "#171614"    # 深墨
RED = "#d4532a"     # 强调
GRAY = "#857f73"    # 主灰
GRAY2 = "#b8b0a0"   # 浅灰
GRAY3 = "#cfc7b6"   # 更浅（描边/分隔）

MONO = "Menlo,'Courier New',monospace"
SERIF = "'Songti SC','Noto Serif CJK SC',serif"

out = []
_clip = [0]


def add(s):
    out.append(s)


# ============ 基础绘制 ============

def txt(x, y, s, size=22, fill=INK, weight=400, font=None, anchor=None, op=None):
    a = ' text-anchor="%s"' % anchor if anchor else ""
    o = ' opacity="%s"' % op if op is not None else ""
    f = ' font-family="%s"' % font if font else ""
    return ('<text x="%s" y="%s" fill="%s" font-size="%s" font-weight="%s"%s%s%s>'
            '<tspan leaf="">%s</tspan></text>' % (x, y, fill, size, weight, f, a, o, s))


def rect(x, y, w, h, fill="none", stroke=None, sw=1.2, rx=0, op=None):
    st = ' stroke="%s" stroke-width="%s"' % (stroke, sw) if stroke else ""
    o = ' opacity="%s"' % op if op is not None else ""
    return '<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s"%s%s/>' % (
        x, y, w, h, rx, fill, st, o)


def line(x1, y1, x2, y2, color=GRAY3, sw=1.2, dash=None, op=None):
    d = ' stroke-dasharray="%s"' % dash if dash else ""
    o = ' opacity="%s"' % op if op is not None else ""
    return '<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s"%s%s/>' % (
        x1, y1, x2, y2, color, sw, d, o)


def node(cx, cy, r, color=RED, op=None):
    """6 辐条节点 —— 母题符号"""
    sp = []
    for i in range(6):
        a = math.radians(12 + 60 * i)
        sp.append("M%.0f %.0fL%.1f %.1f" % (
            cx, cy, cx + r * 3.3 * math.cos(a), cy + r * 3.3 * math.sin(a)))
    o = ' opacity="%s"' % op if op is not None else ""
    return ('<g%s><circle cx="%.0f" cy="%.0f" r="%.1f" fill="%s"/>'
            '<path d="%s" stroke="%s" stroke-width="%.2f" fill="none" stroke-linecap="round"/></g>'
            % (o, cx, cy, r, color, "".join(sp), color, r * 1.4))


# ============ 装饰系统（本次补上的关键差距） ============

def grain(x, y, w, h, n=60, seed=0, op=0.16):
    """纸纹噪点：随机短斜线，营造纸张纤维感"""
    rnd = random.Random(seed)
    o = []
    for _ in range(n):
        px = x + rnd.random() * w
        py = y + rnd.random() * h
        L = 2 + rnd.random() * 6
        o.append(line(px, py, px + L, py + L * 0.55, GRAY2, 1,
                      op="%.2f" % (op * (0.4 + rnd.random()))))
    return "".join(o)


def hatch(x, y, w, h, gap=10, op=0.12, color=INK, sw=1.4, seed=0):
    """斜线网纹（riso / 工程图感），带 clipPath 裁切"""
    _clip[0] += 1
    cid = "hc%d" % _clip[0]
    o = ['<clipPath id="%s">%s</clipPath>' % (cid, rect(x, y, w, h, "#fff"))]
    o.append('<g clip-path="url(#%s)" opacity="%s">' % (cid, op))
    i = 0
    while x + i * gap < x + w + h:
        px = x + i * gap
        o.append(line(px, y + h, px + h, y, color, sw))
        i += 1
    o.append("</g>")
    return "".join(o)


def dots_bg(x, y, w, h, gap=26, r=1.6, op=0.20, color=GRAY2):
    """半调网点底纹"""
    o = ['<g opacity="%s">' % op]
    yy = y
    row = 0
    while yy < y + h:
        xx = x + (gap / 2 if row % 2 else 0)
        while xx < x + w:
            o.append('<circle cx="%.0f" cy="%.0f" r="%s" fill="%s"/>' % (xx, yy, r, color))
            xx += gap
        yy += gap * 0.87
        row += 1
    o.append("</g>")
    return "".join(o)


def ruler(x, y, w, ticks=26, label=None, color=GRAY3):
    """刻度尺：细密竖线 + 端头数字，增加工程精密感"""
    o = [line(x, y, x + w, y, color, 1.4)]
    step = w / ticks
    for i in range(ticks + 1):
        px = x + i * step
        o.append(line(px, y, px, y + (9 if i % 5 == 0 else 5), color, 1.2))
    if label:
        o.append(txt(x + w + 8, y + 4, label, 17, GRAY, font=MONO))
    return "".join(o)


def blocks(x, y, n, filled=0, w=8, h=16, gap=11, color=RED):
    """进度块序列（样本页脚同款）"""
    return "".join(rect(x + i * gap, y, w, h, color if i < filled else "none", INK, 1.2)
                   for i in range(n))


def tag(x, y, s, color=GRAY, fill="none", pad=8, size=17):
    """伪 UI 标签：等宽小字 + 细框（样本里 CTX 35% 那类）"""
    w = len(s) * size * 0.62 + pad * 2
    return (rect(x, y, w, size + pad * 1.4, fill, color, 1.2, 3) +
            txt(x + pad, y + size + pad * 0.42, s, size, color, font=MONO))


def corner(x, y, s=16, color=GRAY3, sw=1.4):
    """角标：L 形细线"""
    return line(x, y + s, x, y, color, sw) + line(x, y, x + s, y, color, sw)


def handarrow(x1, y1, x2, y2, bow=0.22, color=RED, sw=3, head=13):
    """手绘感箭头：略弯的曲线 + 分叉箭头"""
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy) or 1
    nx, ny = -dy / L, dx / L
    cx, cy = mx + nx * L * bow, my + ny * L * bow
    a = math.atan2(y2 - cy, x2 - cx)
    h1 = (x2 - head * math.cos(a - 0.42), y2 - head * math.sin(a - 0.42))
    h2 = (x2 - head * math.cos(a + 0.42), y2 - head * math.sin(a + 0.42))
    return ('<path d="M%.1f %.1fQ%.1f %.1f %.1f %.1f" fill="none" stroke="%s" '
            'stroke-width="%s" stroke-linecap="round"/>'
            '<path d="M%.1f %.1fL%.1f %.1fM%.1f %.1fL%.1f %.1f" fill="none" stroke="%s" '
            'stroke-width="%s" stroke-linecap="round"/>'
            % (x1, y1, cx, cy, x2, y2, color, sw,
               x2, y2, h1[0], h1[1], x2, y2, h2[0], h2[1], color, sw))


def scribble(cx, cy, rx, ry, color=RED, sw=2.4, seed=1):
    """手绘圈选：两条略错位的椭圆弧，不闭合"""
    rnd = random.Random(seed)
    o = []
    for k in range(2):
        x1 = cx - rx + rnd.uniform(-6, 6)
        y1 = cy + rnd.uniform(-4, 4)
        x2 = cx + rx + rnd.uniform(-6, 6)
        y2 = cy + rnd.uniform(-4, 4)
        o.append('<path d="M%.1f %.1fA%.1f %.1f 0 1 1 %.1f %.1f" fill="none" stroke="%s" '
                 'stroke-width="%s" stroke-linecap="round" opacity="%.2f"/>'
                 % (x1, y1, rx, ry, x2, y2, color, sw, 0.85 - k * 0.25))
    return "".join(o)


def stamp(x, y, s, color=RED, size=22):
    """印章：细框 + 轻微错位双框（模拟盖歪）"""
    w = len(s) * size * 0.66 + 26
    return (rect(x + 2, y + 2, w, size + 20, "none", color, 1.6, 4, "0.35") +
            rect(x, y, w, size + 20, "none", color, 2.4, 4) +
            txt(x + 13, y + size + 8, s, size, color, font=MONO, weight=700))


def card(x, y, w, h, num=None, label=None, fill=PAPER2, hatch_bg=False, seed=0):
    """卡片：纸底 + 细边框 + 顶部标签 + 对角角标"""
    o = [rect(x, y, w, h, fill, GRAY3, 1.2, 4)]
    if hatch_bg:
        o.append(hatch(x, y, w, h, 12, 0.07, seed=seed))
    o.append(corner(x + 6, y + 6))
    o.append(corner(x + w - 6, y + h - 6))
    if num is not None:
        o.append(txt(x + 14, y + 26, num, 17, GRAY, font=MONO))
    if label:
        o.append(txt(x + w - 14, y + 26, label, 17, GRAY, font=MONO, anchor="end"))
    return "".join(o)


def watermark(y, word, x=504, size=54, op="0.06", color=RED):
    """样本招牌：大字号低透明度转折词铺底"""
    return txt(x, y, word, size, color, weight=700, font=SERIF, op=op)


def breadcrumb(y, s):
    """顶部细导航条"""
    return (line(74, y, 676, y, GRAY3, 1.2) +
            txt(74, y - 10, s, 17, GRAY, font=MONO) +
            txt(676, y - 10, "750 × %d" % H, 17, GRAY, font=MONO, anchor="end"))


def footer(y, page, label):
    return "".join([
        line(74, y - 26, 676, y - 26, GRAY3, 1.2, dash="2 5"),
        txt(74, y, label, 22, GRAY, font=MONO),
        txt(452, y, "P.%02d" % page, 22, GRAY, font=MONO),
        blocks(600, y - 16, 6, min(page, 6)),
    ])


# =========================================================
add('<svg font-family="\'PingFang SC\',\'Noto Sans CJK SC\',sans-serif" '
    'xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" aria-label="zine" '
    'style="display:block;width:100%%;height:auto;overflow:hidden;">' % (W, H))
add(rect(0, 0, W, H, PAPER))

# ---- 背景层：水印词 + 节点网络 + 纸纹（样本的"纸感"来源） ----
add('<g aria-label="far">')
for (wy, ww, wx, ws) in [(200, "然而", 470, 64), (470, "但是", 120, 54),
                         (1180, "于是", 430, 54), (1750, "所以", 150, 60),
                         (2480, "然而", 470, 54), (3050, "但是", 140, 64),
                         (3720, "于是", 420, 54), (4380, "所以", 150, 54),
                         (5020, "然而", 460, 60), (5680, "但是", 130, 54),
                         (6360, "于是", 440, 54), (6860, "所以", 150, 54)]:
    add(watermark(wy, ww, wx, ws))
for (nx, ny, nr) in [(640, 300, 22), (110, 1520, 18), (650, 2180, 20),
                     (120, 2880, 16), (660, 3560, 18), (110, 4240, 20),
                     (640, 4900, 16), (120, 5560, 18), (660, 6200, 20)]:
    add(node(nx, ny, nr, INK, "0.05"))
add(grain(0, 0, W, H, 320, seed=7, op=0.14))
add('</g>')

# ---------- P1 封面 ----------
add(breadcrumb(150, "ZINE / 长卷 SVG 解剖"))
add(tag(74, 176, "ISSUE 001", RED))
add(tag(200, 176, "SMIL · 22.3s", GRAY))
add('<g data-cue="p1-title">' + txt(74, 320, "它是怎么动起来的", 44, INK, weight=700, font=SERIF) + '</g>')
add(line(74, 350, 676, 350, GRAY3, 1.4))
add('<g data-cue="p1-sub">' + txt(74, 404, "一份关于长卷 SVG 的技术小报", 24, RED) + '</g>')
add(txt(74, 452, "复刻《Claude by Claude》，并拆开它的制作链路", 22, GRAY))
add(hatch(74, 480, 290, 90, 11, 0.10, seed=1))
add('<g data-cue="p1-node">' + node(620, 505, 14, RED) + '</g>')
add(txt(566, 438, "(620, 505)", 17, GRAY2, font=MONO))
add(ruler(74, 600, 420, 28, "750px"))
add(footer(650, 1, "NEXT TOKEN #1"))

# ---------- P2 反直觉 ----------
add(breadcrumb(800, "§ 01 · 它不是什么"))
for i, (word, yy) in enumerate([("不是视频", 900), ("不是 GIF", 966), ("不是图片", 1032)]):
    wpx = sum(38 if ord(c) > 127 else 22 for c in word)
    add('<g data-cue="p2-%d">' % (i + 1) +
        txt(74, yy, word, 38, INK, weight=700) +
        line(70, yy - 13, 74 + wpx + 6, yy - 13, RED, 6) + '</g>')
add('<g data-cue="p2-answer">' + txt(74, 1136, "是一段 SVG。", 44, RED, weight=700) + '</g>')
add('<g data-cue="p2-code">' +
    card(74, 1180, 602, 118, num="01", label="viewBox") +
    txt(96, 1230, '&lt;svg viewBox="0 0 750 11980"&gt;', 22, INK, font=MONO) +
    txt(96, 1266, '287KB 源码 · 532 个 text · 0 张位图', 17, GRAY, font=MONO) + '</g>')
add(footer(1350, 2, "NEXT TOKEN #2"))

# ---------- P3 复刻：终端幕 ----------
add(breadcrumb(1500, "§ 02 · 复刻 · 终端幕"))
add('<g data-cue="p3-term">' +
    card(74, 1540, 602, 176, num="TERM", label="sample P.02") +
    txt(104, 1596, "ASSISTANT:", 22, RED, font=MONO, weight=700) +
    '<text x="104" y="1656" fill="%s" font-size="38" font-weight="700" '
    'data-cue="p3-hello"><tspan leaf="">你好。</tspan></text>' % INK + '</g>')
add('<rect data-cue="p3-cursor" x="104" y="1632" width="16" height="34" fill="%s"/>' % INK)
add(handarrow(420, 1630, 320, 1730, 0.3, GRAY, 2.4))
add(txt(430, 1770, "typewriter 0.3s/字", 17, GRAY, font=MONO))
add(txt(74, 1810, "begin=0s · repeatCount=indefinite", 17, GRAY2, font=MONO))
add(footer(2030, 3, "NEXT TOKEN #3"))

# ---------- P4 复刻：点击幕 ----------
add(breadcrumb(2200, "§ 03 · 复刻 · 交互幕"))
NODES = [(180, 2290, 18), (400, 2230, 16), (620, 2330, 20), (300, 2470, 14)]
for i, (cx, cy, r) in enumerate(NODES):
    add('<g data-cue="p4-n%d">' % (i + 1) + node(cx, cy, r, RED) + '</g>')
    add(txt(cx - 30, cy - r * 3.3 - 10, "(%d,%d)" % (cx, cy), 17, GRAY2, font=MONO))
add(scribble(300, 2470, 64, 38, GRAY3, 2.0, seed=3))
add(txt(74, 2580, "[ 点一下，看它们在看谁 ]", 22, GRAY, font=MONO))
for i, d in enumerate([
        "M180 2290Q290 2420 400 2230",
        "M400 2230Q510 2300 620 2330",
        "M620 2330Q460 2510 300 2470",
        "M300 2470Q240 2380 180 2290",
        "M620 2330Q560 2210 400 2230"]):
    add('<g data-cue="p4-l%d"><path d="%s" fill="none" stroke="%s" stroke-width="%s" '
        'stroke-linecap="round"%s/></g>'
        % (i + 1, d, RED, 6 if i < 4 else 4, ' opacity="0.6"' if i == 4 else ""))
add(txt(74, 2660, "begin=click × 5 · fill=freeze · restart=always", 17, GRAY2, font=MONO))
add(footer(2730, 4, "NEXT TOKEN #4"))

# ---------- P5 转折 ----------
add(breadcrumb(2900, "§ 04 · 转折"))
add('<g transform="translate(110 3110)"><g data-cue="p5-q">' +
    txt(0, 0, "？", 64, RED, weight=700, font=SERIF) + '</g></g>')
add('<g data-cue="p5-title">' + txt(230, 3070, "可是，怎么做的？", 38, INK, weight=700) + '</g>')
add('<g data-cue="p5-sub">' + txt(230, 3126, "下面六屏，一层层拆给你看", 22, GRAY) + '</g>')
add(scribble(340, 3070, 230, 62, GRAY3, 2.2, seed=5))
add(footer(3430, 5, "NEXT TOKEN #5"))

# ---------- P6 三段输入 ----------
add(breadcrumb(3600, "§ 05 · 原理 ①  三段输入，一次编译"))
for i, (label, sub) in enumerate([("skeleton.svg", "静态骨架"),
                                  ("timeline.json", "人写的时码"),
                                  ("timeline_compile", "脚本编译")]):
    x = 74 + i * 212
    add('<g data-cue="p6-b%d">' % (i + 1) +
        card(x, 3660, 190, 96, num="0%d" % (i + 1)) +
        txt(x + 14, 3710, label, 20, INK, font=MONO, weight=700) +
        txt(x + 14, 3740, sub, 17, GRAY) + '</g>')
for i in range(3):
    x = 169 + i * 212
    add('<g data-cue="p6-a%d"><path d="M%s 3756Q%s 3808 %s 3830" fill="none" stroke="%s" '
        'stroke-width="2.4" stroke-linecap="round" stroke-dasharray="5 4"/></g>'
        % (i + 1, x, x, 375, RED))
add('<g data-cue="p6-out">' +
    card(250, 3850, 250, 96, num="OUT", label="17 animate", fill=PAPER3, hatch_bg=True) +
    txt(268, 3906, "zine.svg", 22, RED, font=MONO, weight=700) + '</g>')
add(footer(4130, 6, "NEXT TOKEN #6"))

# ---------- P7 keyTimes（预写 7s 循环） ----------
add(breadcrumb(4300, "§ 06 · 原理 ②  人不手写 keyTimes"))
add(card(74, 4360, 602, 292, num="CALC", label="T = 22.3s", hatch_bg=True, seed=2))
add(txt(100, 4416, "cue:  at 3.4s   dur 1.6s   T 22.3s", 22, INK, font=MONO))
T7 = 7.0
for i, (s, yy, col, wt) in enumerate([
        ("a = 3.4 / 22.3", 4466, INK, 400),
        ("  = 0.1525", 4500, GRAY, 400),
        ("b = 5.0 / 22.3", 4538, INK, 400),
        ("  = 0.2242", 4572, GRAY, 400)]):
    a = 0.12 + i * 0.10
    add('<g visibility="hidden">'
        '<animate attributeName="visibility" values="hidden;visible;visible;hidden" '
        'keyTimes="0;%.3f;0.93;1" calcMode="discrete" begin="0s" dur="%.1fs" repeatCount="indefinite"/>'
        % (a, T7) + txt(100, yy, s, 22, col, font=MONO, weight=wt) + '</g>')
add('<g data-cue="p7-result" visibility="hidden">'
    '<animate attributeName="visibility" values="hidden;visible;visible;hidden" '
    'keyTimes="0;0.52;0.93;1" calcMode="discrete" begin="0s" dur="%.1fs" repeatCount="indefinite"/>'
    % T7 + txt(100, 4626, 'keyTimes="0;0.1525;0.2242;1"', 24, RED, font=MONO, weight=700) + '</g>')
add(txt(74, 4690, "四段式：0→a 隐 · a→b 渐变 · b→1 保持", 17, GRAY2, font=MONO))
add(footer(4830, 7, "NEXT TOKEN #7"))

# ---------- P8 注入（预写 6.4s 循环） ----------
add(breadcrumb(4980, "§ 07 · 原理 ③  编译 = 把时码写进骨架"))
add(card(74, 5040, 268, 172, num="BEFORE"))
add(txt(94, 5096, '&lt;g data-cue="hero"&gt;', 20, INK, font=MONO))
add(txt(94, 5132, "  &lt;text&gt;…&lt;/text&gt;", 20, GRAY, font=MONO))
add(txt(94, 5168, '&lt;/g&gt;', 20, INK, font=MONO))
add('<g visibility="hidden" stroke-dasharray="100 100" stroke-dashoffset="100">'
    '<animate attributeName="visibility" values="hidden;visible;visible;hidden" keyTimes="0;0.08;0.9;1" '
    'calcMode="discrete" begin="0s" dur="6.4s" repeatCount="indefinite"/>'
    '<animate attributeName="stroke-dashoffset" values="100;100;0;0" keyTimes="0;0.08;0.34;1" '
    'begin="0s" dur="6.4s" repeatCount="indefinite"/>'
    '<path d="M362 5116L404 5116" pathLength="100" fill="none" stroke="%s" stroke-width="3" '
    'stroke-linecap="round"/></g>' % RED)
add(card(416, 5040, 260, 210, num="AFTER", label="+animate", fill=PAPER3))
add('<g visibility="hidden">'
    '<animate attributeName="visibility" values="hidden;visible;visible;hidden" keyTimes="0;0.36;0.9;1" '
    'calcMode="discrete" begin="0s" dur="6.4s" repeatCount="indefinite"/>'
    + txt(436, 5096, '&lt;g data-cue="hero"&gt;', 20, INK, font=MONO)
    + txt(436, 5132, '  &lt;animate/&gt;', 20, RED, font=MONO, weight=700)
    + txt(436, 5168, '  &lt;text&gt;…&lt;/text&gt;', 20, GRAY, font=MONO)
    + txt(436, 5204, '&lt;/g&gt;', 20, INK, font=MONO) + '</g>')
add(txt(74, 5300, "元素上打个 data-cue，脚本就能找到它", 17, GRAY2, font=MONO))
add(footer(5410, 8, "NEXT TOKEN #8"))

# ---------- P9 嵌套 + 冒泡（预写 5.8s 循环） ----------
add(breadcrumb(5560, "§ 08 · 原理 ④  点击靠嵌套层 + 透明热区"))
add(txt(74, 5624, "visibility:hidden 的元素收不到点击 ——", 22, GRAY))
add(txt(74, 5656, "所以要把 N 个元素嵌成 N 层，热区放最内层", 22, GRAY))
LY = [(90, 5720, 570, 430, "Layer 1  keyTimes 0;0;1"),
      (130, 5770, 490, 340, "Layer 2  keyTimes 0;0.0229;1"),
      (170, 5820, 410, 250, "Layer 3  keyTimes 0;0.0457;1")]
for i, (x, y, w, h, label) in enumerate(LY):
    add(rect(x, y, w, h, "none", INK if i == 0 else GRAY2, 1.4, 10))
    add(txt(x + 14, y + 28, label, 17, GRAY, font=MONO))
    a = 0.42 + i * 0.07
    add('<g visibility="hidden">'
        '<animate attributeName="visibility" values="hidden;visible;visible;hidden" '
        'keyTimes="0;%.3f;0.92;1" calcMode="discrete" begin="0s" dur="5.8s" repeatCount="indefinite"/>'
        % a + rect(x, y, w, h, "none", RED, 2.2, 10) + '</g>')
add(line(210, 5980, 540, 5980, GRAY, 1.4, dash="4 4") + line(210, 6026, 540, 6026, GRAY, 1.4, dash="4 4") + line(210, 5980, 210, 6026, GRAY, 1.4, dash="4 4") + line(540, 5980, 540, 6026, GRAY, 1.4, dash="4 4"))
add(txt(226, 6010, 'pointer-events="all"', 17, GRAY, font=MONO))
# 两个节点 + 三条待生长的线 —— P.04 交互的缩小版，线条有起止语义
add(node(240, 5920, 10, RED))
add(node(470, 5940, 8, RED))
add(txt(180, 5880, "(240, 5920)", 17, GRAY2, font=MONO))
add(txt(432, 5896, "(470, 5940)", 17, GRAY2, font=MONO))

# 气泡沿虚线轨迹从热区垂直上升，穿过三层
add(line(520, 6026, 520, 5760, GRAY2, 1.2, dash="3 5", op="0.75"))
add('<g>'
    '<animateTransform attributeName="transform" type="translate" '
    'values="0 0;0 0;0 -250;0 -250;0 0" keyTimes="0;0.14;0.40;0.88;1" '
    'begin="0s" dur="5.8s" repeatCount="indefinite"/>'
    '<circle cx="520" cy="6003" r="12" fill="%s"/></g>' % RED)
add(txt(210, 6052, "↑ 点击后事件沿冒泡穿过每一层", 17, GRAY2, font=MONO))
for i, d in enumerate(["M240 5920Q350 5860 470 5940",
                       "M240 5920Q330 5980 470 5940",
                       "M240 5920Q400 5880 470 5940"]):
    a = 0.62 + i * 0.05
    add('<g visibility="hidden" stroke-dasharray="100 100" stroke-dashoffset="100">'
        '<animate attributeName="visibility" values="hidden;visible;visible;hidden" '
        'keyTimes="0;%.3f;0.92;1" calcMode="discrete" begin="0s" dur="5.8s" repeatCount="indefinite"/>'
        % a +
        '<animate attributeName="stroke-dashoffset" values="100;100;0;0;100" '
        'keyTimes="0;%.3f;%.3f;0.88;1" begin="0s" dur="5.8s" repeatCount="indefinite"/>'
        % (a, min(0.86, a + 0.16)) +
        '<path d="%s" pathLength="100" fill="none" stroke="%s" stroke-width="4" '
        'stroke-linecap="round"/></g>' % (d, RED))
add(txt(74, 6186, "各层 animate 同时 begin，靠递增的 keyTimes 错开先后", 22, INK, weight=700))
add(txt(74, 6220, "—— stagger 是结构造的，不是动画属性", 22, INK, weight=700))
add(footer(6262, 9, "NEXT TOKEN #9"))

# ---------- P10 体检 · 发布 ----------
add(breadcrumb(6400, "§ 09 · 原理 ⑤  体检 · 预览 · 发布"))
checks = ["values 与 keyTimes 段数一致",
          "keyTimes 单调递增，首 0 尾 1",
          "热区在 click 动画的子树内",
          "无 script / 外链 / 非系统字体"]
for i, c in enumerate(checks):
    add('<g data-cue="p10-c%d">' % (i + 1) +
        '<path d="M100 %d l13 13 l24 -28" fill="none" stroke="#1D9E75" stroke-width="3" '
        'stroke-linecap="round" stroke-linejoin="round"/>' % (6470 + i * 48) +
        txt(146, 6478 + i * 48, c, 22, INK) + '</g>')
add('<g data-cue="p10-ok">' +
    card(74, 6700, 602, 70, label="PASS · validate_svg.py", fill=PAPER3) +
    txt(104, 6746, "0 error / 0 warn", 24, "#0F6E56", font=MONO, weight=700) + '</g>')
add('<g data-cue="p10-steps">' +
    txt(74, 6840, "375px 预览  →  手机真机确认  →  粘贴公众号", 22, GRAY) + '</g>')
add(stamp(430, 6858, "wechat-animating", INK, 20))
add(footer(6940, 10, "NEXT TOKEN #10"))

add('</svg>')

import os
dst = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skeleton.svg")
open(dst, "w", encoding="utf-8").write("\n".join(out))
print("骨架已生成 -> %s" % dst)
print("  画布 750 x %d（%d 屏）· %d 个绘制节点" % (H, N, len(out)))
