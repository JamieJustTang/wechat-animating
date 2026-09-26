#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_svg.py — 微信长卷 SVG 体检。

退出码: 0 = 通过(可含 warn) / 1 = 有 error(禁止进发布环节)

用法:
  python3 validate_svg.py zine.svg
  python3 validate_svg.py zine.svg --json
"""

import argparse
import json
import os
import re
import sys

FORBIDDEN_TAGS = ["script", "iframe", "object", "embed", "link",
                  "form", "input", "button", "select", "textarea",
                  "video", "audio", "foreignObject"]

SYS_FONTS = ["pingfang sc", "noto sans cjk sc", "songti sc", "noto serif cjk sc",
             "menlo", "courier new", "monospace", "sans-serif", "serif",
             "helvetica", "arial", "system-ui", "-apple-system"]

OK = "  ok  "
WARN = " warn "
ERR = "ERROR "


def check_hotspot_paths(svg):
    """核心机制校验：click 动画所在元素的子树内必须有热区。

    SMIL 的 begin="click" 靠事件冒泡触发。热区若不在同一子树，
    点击永远不会传到那条 animate 上。返回 (缺热区的元素, 通过的数量)。
    """
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(svg)
    except Exception:
        return [], 0

    ns = "{http://www.w3.org/2000/svg}"

    def tag_of(e):
        return e.tag.replace(ns, "") if isinstance(e.tag, str) else ""

    hosts = []
    for parent in root.iter():
        for ch in parent:
            if tag_of(ch) in ("animate", "animateTransform", "set") \
                    and "click" in (ch.get("begin") or ""):
                hosts.append(parent)
                break

    bad, ok = [], 0
    for h in hosts:
        if any(c.get("pointer-events") == "all" for c in h.iter()):
            ok += 1
        else:
            bad.append(h.get("data-cue") or h.get("id") or tag_of(h))
    return bad, ok


def check(svg):
    errors, warns, oks = [], [], []
    size = len(svg.encode("utf-8"))

    # --- 1 禁用标签 ---
    for t in FORBIDDEN_TAGS:
        n = len(re.findall(r"<\s*%s\b" % t, svg, re.I))
        if n:
            errors.append("禁用标签 <%s> x%d — 微信会剥离" % (t, n))
    if not errors:
        oks.append("无 script / iframe / 表单等禁用标签")

    # --- 2 事件属性 ---
    ev = re.findall(r"\son[a-z]+\s*=", svg, re.I)
    jshref = re.findall(r'href\s*=\s*"javascript:', svg, re.I)
    if ev or jshref:
        errors.append("存在 JS 入口: on* x%d, javascript: x%d" % (len(ev), len(jshref)))
    else:
        oks.append("无 on* 事件与 javascript: 链接")

    # --- 3 外链资源 (排除 xmlns) ---
    ext = []
    for m in re.finditer(r'(?:href|src)\s*=\s*"([^"]+)"', svg):
        v = m.group(1)
        if v.startswith(("http://", "https://", "//")) and "w3.org" not in v:
            ext.append(v)
    for m in re.finditer(r"url\(\s*['\"]?(https?:)?//", svg):
        ext.append("url(//...)")
    if ext:
        errors.append("外链资源 %d 处，微信不加载外链: %s" % (len(ext), ext[:3]))
    else:
        oks.append("无外部资源引用（全自包含）")

    # --- 4 字体 ---
    bad_fonts = []
    for m in re.finditer(r"font-family\s*[:=]\s*['\"]?([^'\";>]+)", svg):
        raw = m.group(1)
        for f in [x.strip().strip("'\"").lower() for x in raw.split(",")]:
            if f and f not in SYS_FONTS and not any(s in f for s in SYS_FONTS):
                bad_fonts.append(f)
    if bad_fonts:
        warns.append("疑似非系统字体: %s — 外链字体在微信里必回退" % sorted(set(bad_fonts))[:4])
    else:
        oks.append("字体均在系统字体栈内")

    # --- 5 结构 ---
    vb = re.search(r'viewBox\s*=\s*"([^"]+)"', svg)
    if not vb:
        errors.append("缺少 viewBox — 手机上必然裁切")
    else:
        parts = vb.group(1).split()
        if len(parts) != 4:
            errors.append("viewBox 格式错误: %s" % vb.group(1))
        else:
            try:
                h = float(parts[3])
                oks.append("viewBox 高度 %d" % h)
                if h > 20000:
                    warns.append("viewBox 高度 %d > 20000，建议拆成多段 SVG" % h)
            except ValueError:
                errors.append("viewBox 数值异常: %s" % vb.group(1))

    if "display:block" not in svg.replace(" ", ""):
        warns.append("外层 svg 建议写 style=\"display:block;width:100%;height:auto\"")

    # --- 6 SMIL 合法性 (最容易静默失效的地方) ---
    n_anim = 0
    bad_anim = 0
    click_anim = 0
    for m in re.finditer(r"<(animate|animateTransform|set)\b([^>]*?)/?>", svg):
        n_anim += 1
        tag, attrs_s = m.group(1), m.group(2)
        attrs = dict(re.findall(r'([\w:-]+)\s*=\s*"([^"]*)"', attrs_s))
        vals = attrs.get("values")
        kts = attrs.get("keyTimes")
        if vals and kts:
            nv = len(vals.split(";"))
            nk = len(kts.split(";"))
            if nv != nk:
                bad_anim += 1
                errors.append("%s: values 有 %d 段但 keyTimes 有 %d 段（该动画会静默失效）"
                              % (tag, nv, nk))
                continue
            try:
                ks = [float(x) for x in kts.split(";")]
                if any(ks[i + 1] < ks[i] for i in range(len(ks) - 1)):
                    bad_anim += 1
                    errors.append("%s: keyTimes 非单调递增: %s" % (tag, kts))
                if ks[0] != 0 or abs(ks[-1] - 1.0) > 1e-6:
                    bad_anim += 1
                    errors.append("%s: keyTimes 必须首为 0 尾为 1，实为 %s" % (tag, kts))
            except ValueError:
                bad_anim += 1
                errors.append("%s: keyTimes 含非数值: %s" % (tag, kts))
        if "click" in attrs.get("begin", ""):
            click_anim += 1
            if attrs.get("fill") != "freeze":
                warns.append("begin=click 的动画建议加 fill=\"freeze\"，否则播完回弹")
            if attrs.get("restart") != "always":
                warns.append("begin=click 的动画建议加 restart=\"always\"，否则只能点一次")

    # 点击热区: 微信里 visibility:hidden 的元素收不到点击，必须靠透明热区。
    # 光有热区还不够——热区必须落在 click 动画所在元素的子树里，否则冒泡到不了。
    if click_anim:
        if 'pointer-events="all"' not in svg:
            errors.append("有 %d 条 begin=\"click\" 动画，但没有透明热区 "
                          "(fill-opacity=\"0\" + pointer-events=\"all\") — 点了不会命中"
                          % click_anim)
        else:
            bad_host, ok_host = check_hotspot_paths(svg)
            if bad_host:
                errors.append("有 %d 处 click 动画所在元素的子树里没有热区，点击冒泡不到：%s"
                              % (len(bad_host), ", ".join(bad_host[:4])))
            else:
                oks.append("点击链路通（%d 处 click 动画均有热区在其子树内）" % ok_host)

    if n_anim == 0:
        warns.append("没有任何动画标签 — 这是静态 SVG，确认是否符合预期")
    else:
        oks.append("动画标签 %d 条（点击触发 %d 条）" % (n_anim, click_anim))
        if bad_anim == 0:
            oks.append("SMIL values/keyTimes 全部匹配")

    # --- 7 体积 ---
    if size > 1024 * 1024:
        errors.append("源码 %.2f MB，超过 1MB，微信会卡" % (size / 1024 / 1024))
    elif size > 500 * 1024:
        warns.append("源码 %d KB，偏大（建议 <500KB）" % (size // 1024))
    else:
        oks.append("源码 %d KB" % (size // 1024))

    # --- 8 字号下限 ---
    small = []
    for m in re.finditer(r'font-size\s*=\s*"([^"]+)"', svg):
        try:
            fs = float(re.sub(r"[^\d.]", "", m.group(1)) or 0)
            if 0 < fs < 22:
                small.append(fs)
        except ValueError:
            pass
    if small:
        warns.append("font-size <22 的 %d 处（750 稿宽下手机端 <11px，可能不可读）" % len(small))

    return errors, warns, oks, {
        "bytes": size, "animations": n_anim, "click": click_anim, "bad_anim": bad_anim}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("svg")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.svg):
        print("文件不存在: %s" % args.svg)
        sys.exit(1)

    svg = open(args.svg, encoding="utf-8").read()
    errors, warns, oks, meta = check(svg)

    if args.json:
        print(json.dumps({"errors": errors, "warns": warns, "oks": oks, "meta": meta},
                         ensure_ascii=False, indent=2))
        sys.exit(1 if errors else 0)

    print("微信长卷 SVG 体检 · %s" % os.path.basename(args.svg))
    print("=" * 52)
    for e in errors:
        print("[ERROR] %s" % e)
    for w in warns:
        print("[warn ] %s" % w)
    for o in oks:
        print("[ ok  ] %s" % o)
    print("=" * 52)
    print("%d error / %d warn" % (len(errors), len(warns)))
    if errors:
        print(">> 不可进入发布环节，先修 error。")
        sys.exit(1)
    print(">> 通过。下一步：编辑器预览 → 手机真机确认 → 粘贴公众号。")


if __name__ == "__main__":
    main()
