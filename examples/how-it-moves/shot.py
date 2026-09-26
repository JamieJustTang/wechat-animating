#!/usr/bin/env python3
"""冻结 SMIL 到指定时刻并截图：python3 shot.py <t1> <t2> ...

注意：
- Chrome headless 最小窗口宽 500（375 会被钳制），故用 500 宽，缩放 = 500/750 = 2/3。
- 源坐标(750) -> png 坐标 = ×2/3。
- 必须 --no-sandbox，否则本机 Chrome GPU 沙箱初始化失败。
"""
import subprocess, sys, os, time

HERE = os.path.dirname(os.path.abspath(__file__))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
WIN = (500, 1868)


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def build_html(t, path):
    svg = read(os.path.join(HERE, "zine.svg"))
    html = ('<!doctype html><html><head><meta charset="utf-8"></head>'
            '<body style="margin:0;background:#fff"><div id="w">' + svg + '</div>'
            '<script>'
            'var s=document.querySelector("#w svg");'
            's.pauseAnimations();s.setCurrentTime(%s);'
            '</script></body></html>' % t)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def shot(t, tag):
    hp = os.path.join(HERE, "_shot_%s.html" % tag)
    build_html(t, hp)
    png = os.path.join(HERE, "shot_%s.png" % tag)
    if os.path.exists(png):
        os.remove(png)
    cmd = [CHROME, "--headless=new", "--no-sandbox", "--disable-gpu",
           "--hide-scrollbars", "--virtual-time-budget=1500",
           "--screenshot=" + png,
           "--window-size=%d,%d" % WIN, hp]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(30):
        if os.path.exists(png) and os.path.getsize(png) > 1000:
            break
        time.sleep(0.2)
    print("t=%s -> %s (%d B)" % (t, png, os.path.getsize(png) if os.path.exists(png) else 0))
    os.remove(hp)


if __name__ == "__main__":
    for t in sys.argv[1:]:
        shot(t, "t%s" % str(t).replace(".", "_"))
