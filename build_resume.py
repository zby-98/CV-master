#!/usr/bin/env python3
"""
AI Resume Tailoring Agent - CLI (Multi-User)
============================================
用法:
  python build_resume.py init --user <用户名>
  python build_resume.py build --user <用户名> --mode import <文件>
  python build_resume.py build --user <用户名> --mode chat
  python build_resume.py tailor --user <用户名> --jd <JD文件>
"""

import argparse
import sys
import textwrap
from pathlib import Path

from core import (
    PROJECT_DIR,
    load_config, require_api_key,
    ResumeDatabase, AIClient, TypstCompiler,
    import_resume, chat_extract_yaml, CHAT_SYSTEM_PROMPT,
    create_user, list_users, list_outputs,
    get_user_outputs,
)


def cmd_init(args):
    u = args.user or "default"
    create_user(u)
    print(f"✅ 已为用户 {u} 创建数据目录: data/{u}/")


def cmd_build(args):
    config = load_config()
    require_api_key(config)
    u = args.user or "default"

    if args.mode == "import":
        if not args.file:
            print("❌ mode=import 需要 --file <文件路径>")
            sys.exit(1)
        result = import_resume(config, args.file, user=u)
        if result["success"]:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result['message']}")

    elif args.mode == "chat":
        print(f"🎙️  对话式简历录入 (用户: {u})\n")
        client = AIClient(config)
        messages = []
        while True:
            try:
                ui = input("👤 你: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n👋 结束。")
                break
            if not ui:
                continue
            if ui.lower() in ("完成", "done", "quit"):
                result = chat_extract_yaml(config, messages, user=u)
                if result["success"]:
                    print(f"✅ {result['message']}")
                    print(result["summary"])
                else:
                    print(f"❌ {result['message']}")
                break
            messages.append({"role": "user", "content": ui})
            reply = client.chat(CHAT_SYSTEM_PROMPT, ui, temperature=0.7)
            messages.append({"role": "assistant", "content": reply})
            print(f"🤖 {reply}\n")


def cmd_tailor(args):
    config = load_config()
    require_api_key(config)
    u = args.user or "default"

    jd_path = Path(args.jd)
    if not jd_path.exists():
        print(f"❌ JD 文件不存在: {jd_path}")
        sys.exit(1)
    jd_text = jd_path.read_text(encoding="utf-8")

    db = ResumeDatabase(u)
    db.load()

    prompt_path = PROJECT_DIR / "prompts" / "system_prompt.md"
    if prompt_path.exists():
        prompt_template = prompt_path.read_text(encoding="utf-8")
    else:
        prompt_template = "{jd_text}\n\n{master_yaml}"

    client = AIClient(config)
    print("🤖 AI 分析中...")
    typst_code = client.tailor_pipeline(jd_text, db.to_yaml_string(), prompt_template)
    typst_code = _clean_code_fence(typst_code, "typst")

    compiler = TypstCompiler(u)
    pdf_path, ok, msg = compiler.compile(typst_code, args.output)
    if ok:
        print(f"✅ PDF: {pdf_path}")
    else:
        print(f"❌ 编译失败:\n{msg}")


def cmd_users(args):
    users = list_users()
    if not users:
        print("暂无用户。使用: python build_resume.py init --user <用户名>")
        return
    print(f"{'用户名':<16} {'数据库':<8} {'创建时间'}")
    print("-" * 40)
    for u in users:
        print(f"{u['name']:<16} {'✅' if u['has_db'] else '🆕':<8} {u['created']}")


def _clean_code_fence(text: str, lang: str = "") -> str:
    text = text.strip()
    if lang and text.startswith(f"```{lang}"):
        text = text[len(f"```{lang}"):]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def main():
    parser = argparse.ArgumentParser(description="AI Resume Tailoring Agent (Multi-User)")
    sub = parser.add_subparsers(dest="command")

    p_init = sub.add_parser("init", help="创建新用户")
    p_init.add_argument("--user", required=True, help="用户名")

    p_users = sub.add_parser("users", help="列出所有用户")

    p_build = sub.add_parser("build", help="构建简历数据库")
    p_build.add_argument("--user", required=True)
    p_build.add_argument("--mode", required=True, choices=["import", "chat"])
    p_build.add_argument("--file")

    p_tailor = sub.add_parser("tailor", help="定制简历")
    p_tailor.add_argument("--user", required=True)
    p_tailor.add_argument("--jd", required=True)
    p_tailor.add_argument("--output", default="tailored_cv")

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "init":
        cmd_init(args)
    elif args.command == "users":
        cmd_users(args)
    elif args.command == "build":
        cmd_build(args)
    elif args.command == "tailor":
        cmd_tailor(args)


if __name__ == "__main__":
    main()
