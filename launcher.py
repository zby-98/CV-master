#!/usr/bin/env python3
"""CV-Assistant 桌面启动器 — PyInstaller 入口点。"""
import os
import sys
import threading
import webbrowser

from app import app


def _open_browser(port: int):
    webbrowser.open(f"http://127.0.0.1:{port}")


def main():
    port = int(os.environ.get("CV_PORT", "8080"))

    # 延迟 0.5 秒打开浏览器，等 Flask 启动好
    threading.Timer(0.5, _open_browser, args=[port]).start()

    print(f"""
╔══════════════════════════════════════╗
║   🎯 AI Resume Tailoring Agent       ║
║   浏览器访问: http://127.0.0.1:{port}   ║
╚══════════════════════════════════════╝
""")
    app.run(debug=False, host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
