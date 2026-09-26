#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
serve.py — 起一个本地静态服务并打开 zine 编辑器。

file:// 下剪贴板 API 若被浏览器限制（写富文本失败），用本脚本。

用法:
  python3 serve.py          # 默认 8733 端口
  python3 serve.py 9000
"""

import http.server
import os
import socketserver
import sys
import webbrowser

APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app")
APP = os.path.abspath(APP)


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=APP, **kw)

    def log_message(self, fmt, *args):
        pass


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8733
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", port), Handler) as httpd:
        url = "http://127.0.0.1:%d/zine-editor.html" % port
        print("zine 编辑器: %s" % url)
        print("Ctrl-C 结束")
        try:
            webbrowser.open(url)
        except Exception:
            pass
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n已停止")


if __name__ == "__main__":
    main()
