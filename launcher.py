#!/usr/bin/env python3
"""CV-Assistant 桌面启动器 — 原生窗口，无需浏览器。"""
import os
import sys
import threading

import webview
from waitress import serve
from app import app


def _run_flask(port: int):
    serve(app, host="127.0.0.1", port=port, threads=6)


def main():
    port = int(os.environ.get("CV_PORT", "8080"))

    flask_thread = threading.Thread(target=_run_flask, args=[port], daemon=True)
    flask_thread.start()

    webview.create_window(
        title="CV-Assistant - AI 简历定制助手",
        url=f"http://127.0.0.1:{port}",
        width=1280,
        height=860,
        min_size=(900, 600),
        text_select=True,
    )
    webview.start()


if __name__ == "__main__":
    main()
