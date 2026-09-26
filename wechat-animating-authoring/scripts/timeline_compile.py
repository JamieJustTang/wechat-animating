#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
timeline_compile.py — 把人写的时间轴 DSL 编译成 SMIL <animate> 属性，并注入静态 SVG。

用法:
  python3 timeline_compile.py compile timeline.json [-o plan.json]
  python3 timeline_compile.py inject  timeline.json skeleton.svg -o zine.svg [--force]

静态 SVG 里用 data-cue="id" 标记要动的元素:
  <g data-cue="hero"><text>...</text></g>

设计原则: 人不手写 keyTimes。所有归一化比例由本脚本计算。
"""

import argparse
import json
import re
import sys

# ---------- 数值格式化 ----------

def num(x):
    """去掉浮点噪音: 0.0896860986547 -> 0.0897 ; 3.0 -> 3"""
    if isinstance(x, bool):
        return str(x).lower()
    try:
        f = float(x)
    except (TypeError, ValueError):
        return str(x)
    r = round(f, 4)
    if r == int(r):
        return str(int(r))
    return ("%.4f" % r).rstrip("0").rstrip(".")


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, float(x)))


def kt(*vals):
    """生成 keyTimes 字符串, 保证单调不减 + 尾段为 1"""
    out = [clamp(v) for v in vals]
    for i in range(1, len(out)):
        if out[i] < out[i - 1]:
            out[i] = out[i - 1]
    out[-1] = 1.0
    return ";".join(num(v) for v in out)


# ---------- 主时间轴 cues ----------

def compile_cue(cue, T):
    """一次性动作 -> 挂在 T 秒大周期上的 animate 列表"""
    eid = cue.get("id")
    at = float(cue.get("at", 0.0))
    dur = float(cue.get("dur", 1.0))
    fx = cue.get("effect", "fade-in")
    a = clamp(at / T)
    b = clamp((at + dur) / T)

    base = {
        "begin": "0s",
        "dur": num(T) + "s",
        "repeatCount": "indefinite",
    }

    def A(**kw):
        d = dict(base)
        d.update(kw)
        return {"tag": "animate", "attrs": _order(d)}

    def AT(**kw):
        d = dict(base)
        d.update(kw)
        return {"tag": "animateTransform", "attrs": _order(d)}

    if fx == "fade-in":
        return [A(attributeName="opacity", values="0;0;1;1", keyTimes=kt(0, a, b, 1))]
    if fx == "fade-out":
        return [A(attributeName="opacity", values="1;1;0;0", keyTimes=kt(0, a, b, 1))]
    if fx == "appear":
        return [A(attributeName="visibility", calcMode="discrete",
                  values="hidden;hidden;visible;visible", keyTimes=kt(0, a, b, 1))]
    if fx == "vanish":
        return [A(attributeName="visibility", calcMode="discrete",
                  values="visible;visible;hidden;hidden", keyTimes=kt(0, a, b, 1))]
    if fx == "flash":
        return [A(attributeName="opacity", values="1;1;0;0;1;1",
                  keyTimes=kt(0, a, a, b, b, 1))]
    if fx == "rise":
        dy = num(cue.get("dy", 12))
        return [A(attributeName="opacity", values="0;0;1;1", keyTimes=kt(0, a, b, 1)),
                AT(type="translate", values="0 %s;0 %s;0 0;0 0" % (dy, dy),
                   keyTimes=kt(0, a, b, 1))]
    if fx == "sink":
        dy = num(cue.get("dy", 12))
        return [A(attributeName="opacity", values="1;1;0;0", keyTimes=kt(0, a, b, 1)),
                AT(type="translate", values="0 0;0 0;0 %s;0 %s" % (dy, dy),
                   keyTimes=kt(0, a, b, 1))]
    if fx == "wipe":
        dx = num(cue.get("dx", 100))
        return [A(attributeName="opacity", values="0;0;1;1", keyTimes=kt(0, a, b, 1)),
                AT(type="translate", values="-%s 0;-%s 0;0 0;0 0" % (dx, dx),
                   keyTimes=kt(0, a, b, 1))]
    if fx == "draw":
        L = num(cue.get("length", 100))
        return [A(attributeName="visibility", calcMode="discrete",
                  values="hidden;hidden;visible;visible", keyTimes=kt(0, a, b, 1)),
                A(attributeName="stroke-dashoffset", values="%s;%s;0;0" % (L, L),
                  keyTimes=kt(0, a, b, 1))]
    raise ValueError("未知 cue effect: %s (id=%s)" % (fx, eid))


# ---------- 独立循环 loops ----------

def compile_loop(loop):
    eid = loop.get("id")
    fx = loop.get("effect")
    D = num(loop.get("dur", 2.0))
    base = {"begin": "0s", "dur": D + "s", "repeatCount": "indefinite"}

    def A(**kw):
        d = dict(base); d.update(kw)
        return {"tag": "animate", "attrs": _order(d)}

    def AT(**kw):
        d = dict(base); d.update(kw)
        return {"tag": "animateTransform", "attrs": _order(d)}

    if fx == "blink":
        return [A(attributeName="opacity", values="1;1;0;0", keyTimes="0;.5;.5;1")]
    if fx == "flicker":
        return [A(attributeName="opacity", values="1;1;0;1;1",
                  keyTimes="0;.92;.95;.98;1")]
    if fx == "pulse":
        frm = num(loop.get("from", 1)); to = num(loop.get("to", 0.4))
        return [A(attributeName="opacity", values="%s;%s;%s" % (frm, to, frm),
                  keyTimes="0;.5;1")]
    if fx == "breathe":
        dy = num(loop.get("dy", -12))
        return [AT(type="translate", values="0 0;0 %s;0 0" % dy)]
    if fx == "swing":
        amp = num(loop.get("amp", 8))
        cx, cy = _pivot(loop, eid)
        return [AT(type="rotate",
                   values="-%s %s %s;%s %s %s;-%s %s %s" % (amp, cx, cy, amp, cx, cy, amp, cx, cy))]
    if fx == "spin":
        cx, cy = _pivot(loop, eid)
        return [AT(type="rotate", values="0 %s %s;360 %s %s" % (cx, cy, cx, cy))]
    raise ValueError("未知 loop effect: %s (id=%s)" % (fx, eid))


def _pivot(spec, eid):
    p = spec.get("pivot")
    if not p or len(p) != 2:
        raise ValueError("effect 需要 pivot: [cx, cy]  (id=%s)" % eid)
    return num(p[0]), num(p[1])


# ---------- 点击交互 interactive ----------

def compile_interactive(spec):
    """点击触发。

    关键: 微信里 <g visibility="hidden"> 收不到点击。样本文章的做法是
    ——把 N 个元素嵌成 N 层 g，最内层放一个透明热区 rect；点击热区后事件
    沿冒泡路径依次穿过每一层，各层的 animate 同时被触发，靠各自的
    keyTimes 形成 stagger。所以这里返回的是「按层组织」的结构，
    而不是「按元素」的。
    """
    ids = spec.get("ids") or [spec.get("id")]
    fx = spec.get("effect", "reveal")
    D = float(spec.get("dur", 5.25))
    stagger = float(spec.get("stagger", 0.12))
    L = num(spec.get("length", 100))
    freeze = spec.get("freeze", True)

    base = {"begin": "click", "dur": num(D) + "s", "restart": "always"}
    if freeze:
        base["fill"] = "freeze"

    layers = []
    for i, eid in enumerate(ids):
        s = clamp(i * stagger / D, 0, 0.9)

        def A(**kw):
            d = dict(base); d.update(kw)
            return {"tag": "animate", "attrs": _order(d)}

        if fx == "draw-stagger":
            items = [
                A(attributeName="visibility", calcMode="discrete",
                  values="hidden;visible;visible", keyTimes="0;%s;1" % num(s)),
                A(attributeName="stroke-dashoffset", values="%s;%s;0;0" % (L, L),
                  keyTimes=kt(0, s, min(1.0, s + 0.19), 1)),
            ]
            init = {"visibility": "hidden",
                    "stroke-dasharray": "%s %s" % (L, L),
                    "stroke-dashoffset": L}
        elif fx in ("reveal-stagger", "reveal"):
            items = [
                A(attributeName="visibility", calcMode="discrete",
                  values="hidden;visible;visible", keyTimes="0;%s;1" % num(s)),
                A(attributeName="opacity", values="0;1;1",
                  keyTimes=kt(0, s, min(1.0, s + 0.12), 1)),
            ]
            init = {"visibility": "hidden"}
        else:
            raise ValueError("未知 interactive effect: %s" % fx)
        layers.append({"id": eid, "items": items, "init": init})

    return {"spec": spec, "layers": layers}


# ---------- 组装 ----------

def _order(attrs):
    """固定属性输出顺序, 便于 diff"""
    order = ["type", "attributeName", "calcMode", "values", "keyTimes",
             "begin", "dur", "fill", "restart", "repeatCount"]
    out = {}
    for k in order:
        if k in attrs and attrs[k] is not None:
            out[k] = attrs[k]
    for k, v in attrs.items():
        if k not in out:
            out[k] = v
    return out


def compile_plan(doc):
    T = float(doc.get("timeline", {}).get("duration", 22.3))
    loop = doc.get("timeline", {}).get("loop", True)
    plan = {}
    stats = {"cues": 0, "loops": 0, "interactive": 0}

    def push(eid, items):
        plan.setdefault(eid, [])
        for it in items:
            if not loop:
                it["attrs"].pop("repeatCount", None)
                it["attrs"]["repeatCount"] = "1"
            plan[eid].append(it)

    for cue in doc.get("cues", []):
        push(cue["id"], compile_cue(cue, T))
        stats["cues"] += 1
    for lp in doc.get("loops", []):
        push(lp["id"], compile_loop(lp))
        stats["loops"] += 1

    # interactive 不进 plan：它要包成嵌套层，不能平铺注入元素
    groups = [compile_interactive(s) for s in doc.get("interactive", [])]
    stats["interactive"] = sum(len(g["layers"]) for g in groups)

    return {"duration": T, "stats": stats, "plan": plan, "interactive": groups}


def render_animates(items, indent):
    pad = " " * indent
    out = []
    for it in items:
        attrs = " ".join('%s="%s"' % (k, v) for k, v in it["attrs"].items())
        out.append("%s<%s %s/>" % (pad, it["tag"], attrs))
    return "\n".join(out)


# ---------- 注入 ----------

CUE_RE = re.compile(
    r"<(?P<tag>[a-zA-Z][\w:-]*)(?P<pre>[^>]*?)\sdata-cue=\"(?P<id>[^\"]+)\"(?P<post>[^>]*?)(?P<self>/?)>")


def _uses_normalized_length(plan, groups=None):
    """只要有一条 draw 用默认的 100 归一化，就需要给 path 补 pathLength"""
    def scan(items):
        for it in items:
            if it["attrs"].get("attributeName") == "stroke-dashoffset":
                if str(it["attrs"].get("values", "")).split(";")[0].strip() == "100":
                    return True
        return False

    for items in plan.values():
        if scan(items):
            return True
    for g in (groups or []):
        for ly in g["layers"]:
            if scan(ly["items"]):
                return True
    return False


def apply_typewriter(svg, specs, T, loop=True):
    """逐字打字机：把 <text data-cue="x"><tspan>内容</tspan></text>
    拆成逐字 tspan，每个字挂一条 discrete visibility animate，
    起始时刻 at + i*per 依次递增。

    逐字 tspan 不加 dx——字符按自然步进排布（CJK 一字宽 ≈ 1em，
    hidden 的字仍占位，不会回流）。光标每字平移一个 font-size，
    恰好落在最新可见字的右缘。注意：光标步进按等宽假设，
    打字机文本建议用纯中文/全角字符，中英混排会漂移。
    """
    total = 0
    for spec in specs:
        eid = spec.get("id")
        at = float(spec.get("at", 0.0))
        per = float(spec.get("per", 0.28))
        pat = re.compile(
            r'<text([^>]*?)\sdata-cue="%s"([^>]*)>\s*'
            r'<tspan leaf="">([^<]*)</tspan>\s*</text>' % re.escape(eid))
        m = pat.search(svg)
        if not m:
            print("  [!] typewriter: 找不到 data-cue=\"%s\" 的 <text><tspan></text>" % eid)
            continue
        pre, post, content = m.group(1), m.group(2), m.group(3)
        fsm = re.search(r'font-size="([\d.]+)"', pre + post)
        fs = float(fsm.group(1)) if fsm else 24.0

        chars = list(content)
        parts = []
        for i, ch in enumerate(chars):
            a = clamp((at + i * per) / T, 0, 0.985)
            rc = 'repeatCount="indefinite"' if loop else 'repeatCount="1"'
            parts.append(
                '<tspan leaf="">%s'
                '<animate attributeName="visibility" values="hidden;visible;visible" '
                'keyTimes="0;%s;1" calcMode="discrete" begin="0s" dur="%ss" %s/></tspan>'
                % (ch, num(a), num(T), rc))
        total += len(chars)
        svg = (svg[:m.start()] +
               '<text%s data-cue="%s"%s>%s</text>' % (pre, eid, post, "".join(parts)) +
               svg[m.end():])

        # 光标跟随：discrete translate，每出一字跳一个字宽
        cid = spec.get("cursor")
        if cid:
            n = len(chars)
            vals = ";".join("%d 0" % (i * fs) for i in range(n + 1)) + \
                   ";%d 0" % (n * fs)
            kts = ["0"] + [num(clamp((at + i * per) / T, 0, 0.985)) for i in range(n)] + ["1"]
            anim = ('<animateTransform attributeName="transform" type="translate" '
                    'values="%s" keyTimes="%s" calcMode="discrete" begin="0s" '
                    'dur="%ss" repeatCount="%s"/>'
                    % (vals, ";".join(kts), num(T),
                       "indefinite" if loop else "1"))
            cm = re.search(r'<([a-zA-Z][\w:-]*)([^>]*?)\sdata-cue="%s"([^>]*?)(/?)>'
                           % re.escape(cid), svg)
            if not cm:
                print("  [!] typewriter: 找不到 cursor data-cue=\"%s\"" % cid)
            elif cm.group(4) == "/":
                svg = (svg[:cm.start()] +
                       '<%s%s data-cue="%s"%s>%s</%s>'
                       % (cm.group(1), cm.group(2), cid, cm.group(3), anim, cm.group(1)) +
                       svg[cm.end():])
            else:
                svg = svg[:cm.end()] + anim + svg[cm.end():]
    return svg, total


def find_element_end(s, start):
    """从开标签起始位置找到该元素结束后的索引（按同名标签配对）"""
    m = re.match(r"<([a-zA-Z][\w:-]*)", s[start:])
    if not m:
        return len(s)
    tag = m.group(1)
    gt = s.find(">", start)
    if gt < 0:
        return len(s)
    if s[gt - 1] == "/":
        return gt + 1
    depth, pos = 1, gt + 1
    pat = re.compile(r"</?%s\b" % re.escape(tag))
    while depth > 0:
        mm = pat.search(s, pos)
        if not mm:
            return len(s)
        end = s.find(">", mm.start())
        if end < 0:
            return len(s)
        if s[mm.start():mm.start() + 2] == "</":
            depth -= 1
        elif s[end - 1] != "/":
            depth += 1
        pos = end + 1
    return pos


def wrap_interactive(svg, group, vbh=0):
    """把一组交互元素包成嵌套 g + 透明热区。

    结构（N 层）:
      <g init><animate/>元素1
        <g init><animate/>元素2
          ...
            <g init><animate/>元素N <rect 热区/></g>
          ...
        </g>
      </g>
    点热区 → 事件沿冒泡路径穿过全部 N 层 → 各层 animate 同时 begin，
    靠各自递增的 keyTimes 依次显现。这是微信里唯一可靠的 stagger 做法。
    """
    layers = group["layers"]
    spec = group["spec"]

    spans = []
    for ly in layers:
        m = re.search(r"<[a-zA-Z][\w:-]*[^>]*?\sdata-cue=\"%s\"" % re.escape(ly["id"]), svg)
        if not m:
            print("  [!] interactive: 找不到 data-cue=\"%s\"" % ly["id"])
            continue
        spans.append((m.start(), find_element_end(svg, m.start()), ly))
    if not spans:
        return svg
    spans.sort(key=lambda x: x[0])
    start, end = spans[0][0], spans[-1][1]

    hs = spec.get("hotspot") or [0, 0, 750, vbh or 10000]
    hotspot = ('<rect x="%s" y="%s" width="%s" height="%s" fill="#000" '
               'fill-opacity="0" visibility="visible" pointer-events="all"/>'
               % tuple(num(v) for v in hs))

    inner = ""
    for idx in range(len(spans) - 1, -1, -1):
        s0, e0, ly = spans[idx]
        block = svg[s0:e0]
        init = " ".join('%s="%s"' % (k, v) for k, v in ly["init"].items())
        anims = render_animates(ly["items"], 4)
        body = block + (hotspot if idx == len(spans) - 1 else inner)
        inner = "<g %s>\n%s\n%s\n</g>" % (init, anims, body)

    return svg[:start] + "\n" + inner + "\n" + svg[end:]


def normalize_path_lengths(svg, L="100"):
    """给没有自定义 dasharray 的 path 补 pathLength，使 dasharray=100 归一化成立"""
    def repl(m):
        attrs, selfclose = m.group(1), m.group(2)
        if "pathLength=" in attrs or "stroke-dasharray" in attrs:
            return m.group(0)
        return "<path%s pathLength=\"%s\"%s>" % (attrs, L, selfclose)
    return re.sub(r"<path\b([^>]*?)(/?)>", repl, svg)


def inject(svg_text, plan, force=False):
    stats = {"matched": 0, "inserted": 0, "skipped": 0}
    seen = {}

    def repl(m):
        eid = m.group("id")
        items = plan.get(eid)
        stats["matched"] += 1
        if not items:
            return m.group(0)
        if eid in seen and not force:
            stats["skipped"] += 1
            return m.group(0)
        seen[eid] = True

        tag = m.group("tag")
        pre = m.group("pre")
        post = m.group("post")
        selfclose = m.group("self")

        # 补足初始状态属性
        extra = ""
        need_hidden = any(
            it["attrs"].get("attributeName") == "visibility" and
            str(it["attrs"].get("values", "")).startswith("hidden")
            for it in items)
        if need_hidden and "visibility=" not in (pre + post):
            extra += ' visibility="hidden"'
        need_draw = any(it["attrs"].get("attributeName") == "stroke-dashoffset" for it in items)
        if need_draw:
            L = None
            for it in items:
                if it["attrs"].get("attributeName") == "stroke-dashoffset":
                    L = str(it["attrs"]["values"]).split(";")[0]
                    break
            if "stroke-dasharray=" not in (pre + post):
                extra += ' stroke-dasharray="%s %s"' % (L, L)
            if "stroke-dashoffset=" not in (pre + post):
                extra += ' stroke-dashoffset="%s"' % L

        block = render_animates(items, 2)
        stats["inserted"] += len(items)
        head = "<%s%s data-cue=\"%s\"%s%s%s>" % (tag, pre, eid, post, extra, "")
        if selfclose:
            return head + "\n" + block + "\n</%s>" % tag
        return head + "\n" + block

    out = CUE_RE.sub(repl, svg_text)

    missing = [k for k in plan if k not in seen]
    return out, stats, missing


# ---------- CLI ----------

def main():
    ap = argparse.ArgumentParser(description="时间轴 DSL -> SMIL 动画")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("compile", help="输出 animate 属性方案")
    p1.add_argument("timeline")
    p1.add_argument("-o", "--out")

    p2 = sub.add_parser("inject", help="注入静态 SVG")
    p2.add_argument("timeline")
    p2.add_argument("svg")
    p2.add_argument("-o", "--out", required=True)
    p2.add_argument("--force", action="store_true", help="同一 id 出现多次时全部注入")

    args = ap.parse_args()
    doc = json.load(open(args.timeline, encoding="utf-8"))
    plan_doc = compile_plan(doc)
    plan = plan_doc["plan"]

    if args.cmd == "compile":
        payload = json.dumps(plan_doc, ensure_ascii=False, indent=2)
        if args.out:
            open(args.out, "w", encoding="utf-8").write(payload)
            print("已写出 %s" % args.out)
        else:
            print(payload)
        print("周期 %ss | cues=%d loops=%d interactive=%d | 目标元素 %d 个" %
              (plan_doc["duration"], plan_doc["stats"]["cues"],
               plan_doc["stats"]["loops"], plan_doc["stats"]["interactive"], len(plan)),
              file=sys.stderr)
        return

    svg = open(args.svg, encoding="utf-8").read()
    out, stats, missing = inject(svg, plan, force=args.force)

    # 打字机: 拆字必须在注入之后做（会重写 text 内部结构）
    tw = doc.get("typewriter", [])
    if tw:
        out, nch = apply_typewriter(out, tw, plan_doc["duration"],
                                    doc.get("timeline", {}).get("loop", True))
        print("  打字机: %d 处，拆出 %d 字" % (len(tw), nch))

    # 点击交互: 包成嵌套层 + 热区（平铺注入点不动）
    groups = plan_doc.get("interactive", [])
    if groups:
        vbm = re.search(r'viewBox\s*=\s*"([^"]+)"', out)
        vbh = float(vbm.group(1).split()[3]) if vbm else 0
        for g in groups:
            out = wrap_interactive(out, g, vbh)
        print("  点击交互: %d 组，已包成嵌套层 + 透明热区" % len(groups))

    # 归一化描边: 凡用 length=100 的 draw，必须给 path 补 pathLength="100"，
    # 否则 dasharray="100 100" 只在真实路径前 100 单位生效，线条画一半就断。
    if _uses_normalized_length(plan, groups):
        before = out
        out = normalize_path_lengths(out)
        n = len(re.findall(r'pathLength="100"', out)) - \
            len(re.findall(r'pathLength="100"', before))
        if n:
            print("  补 pathLength=\"100\" 于 %d 条 path（归一化描边）" % n)

    open(args.out, "w", encoding="utf-8").write(out)
    print("注入完成 -> %s" % args.out)
    print("  匹配 data-cue 元素 %d 处, 插入 animate %d 条" % (stats["matched"], stats["inserted"]))
    if stats["skipped"]:
        print("  跳过重复 id %d 处 (加 --force 可全部注入)" % stats["skipped"])
    if missing:
        print("  [!] 这些 id 在 SVG 里没找到 data-cue: %s" % ", ".join(missing))


if __name__ == "__main__":
    main()
