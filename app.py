#!/usr/bin/env python3
"""
AI Resume Tailoring Agent - Web UI (Multi-User)
==============================================
"""

import json
import os
from pathlib import Path

from flask import Flask, render_template, request, jsonify, send_file, Response, stream_with_context
from flask import session as flask_session

from core import (
    load_config, save_config,
    ResumeDatabase, AIClient, TypstCompiler,
    import_resume, chat_extract_yaml, CHAT_SYSTEM_PROMPT,
    list_users, create_user, delete_user, get_user_dir,
    load_chat_history, save_chat_history,
    save_jd, list_jds, get_jd,
    list_outputs, _ensure_typst_import, _patch_typst_metadata,
    INTERVIEW_PREP_PROMPT, _clean_code_fence,
    RESOURCE_DIR,
)

# 打包后模板路径需要显式指定
app = Flask(__name__, template_folder=str(RESOURCE_DIR / "templates"))
app.secret_key = os.urandom(24).hex()

# 开发模式：禁用浏览器缓存，确保每次刷新拿到最新代码
@app.after_request
def _no_cache(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response


# ─── 当前用户管理 ───────────────────────────────────────────────

def current_user() -> str:
    """获取当前选中的用户。"""
    u = flask_session.get("current_user", "")
    if not u:
        users = list_users()
        if users:
            u = users[0]["name"]
            flask_session["current_user"] = u
    return u


# ─── 页面 ──────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ─── API: 用户管理 ──────────────────────────────────────────────

@app.route("/api/users", methods=["GET"])
def api_list_users():
    return jsonify({"users": list_users(), "current": current_user()})


@app.route("/api/users/switch", methods=["POST"])
def api_switch_user():
    data = request.json
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"ok": False, "message": "用户名不能为空"})
    user_dir = get_user_dir(name)
    if not user_dir.exists():
        create_user(name)
    flask_session["current_user"] = name
    return jsonify({"ok": True, "message": f"已切换到 {name}", "user": name})


@app.route("/api/users/create", methods=["POST"])
def api_create_user():
    data = request.json
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"ok": False, "message": "用户名不能为空"})
    create_user(name)
    flask_session["current_user"] = name
    return jsonify({"ok": True, "message": f"用户 {name} 已创建", "user": name})


@app.route("/api/users/delete", methods=["POST"])
def api_delete_user():
    data = request.json
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"ok": False, "message": "用户名不能为空"})
    delete_user(name)
    if flask_session.get("current_user") == name:
        flask_session["current_user"] = ""
    return jsonify({"ok": True, "message": f"用户 {name} 已删除"})


# ─── API: 配置 ───────────────────────────────────────────────────

@app.route("/api/config", methods=["GET"])
def api_get_config():
    cfg = load_config()
    return jsonify({
        "api_key": cfg["api_key"][:8] + "****" if cfg["api_key"] else "",
        "base_url": cfg["base_url"],
        "model": cfg["model"],
        "has_key": bool(cfg["api_key"]),
    })


@app.route("/api/config", methods=["POST"])
def api_save_config():
    data = request.json
    api_key = data.get("api_key", "").strip()
    base_url = data.get("base_url", "").strip()
    model = data.get("model", "").strip()
    if not api_key or not base_url or not model:
        return jsonify({"ok": False, "message": "请填写所有字段"})
    save_config(api_key, base_url, model)
    return jsonify({"ok": True, "message": "配置已保存"})


@app.route("/api/config/test", methods=["POST"])
def api_test_connection():
    cfg = load_config()
    if not cfg["api_key"]:
        return jsonify({"ok": False, "message": "请先配置 API Key"})
    client = AIClient(cfg)
    ok, msg = client.test_connection()
    return jsonify({"ok": ok, "message": msg})


# ─── API: 数据库 ──────────────────────────────────────────────────

@app.route("/api/db/summary", methods=["GET"])
def api_db_summary():
    u = current_user()
    if not u:
        return jsonify({"exists": False})
    db = ResumeDatabase(u)
    if db.exists():
        db.load()
        return jsonify(db.summary())
    return jsonify({"exists": False})


@app.route("/api/db/yaml", methods=["GET"])
def api_db_yaml():
    u = current_user()
    if not u:
        return jsonify({"ok": False, "message": "请先选择用户"})
    db = ResumeDatabase(u)
    if not db.exists():
        return jsonify({"ok": False, "message": "数据库不存在"})
    db.load()
    return jsonify({"ok": True, "yaml": db.to_yaml_string()})


@app.route("/api/db/update", methods=["POST"])
def api_db_update():
    u = current_user()
    if not u:
        return jsonify({"ok": False, "message": "请先选择用户"})
    data = request.json
    yaml_text = data.get("yaml", "")
    if not yaml_text.strip():
        return jsonify({"ok": False, "message": "内容为空"})
    import yaml
    try:
        parsed = yaml.safe_load(yaml_text)
        db = ResumeDatabase(u)
        db.save(parsed)
        return jsonify({"ok": True, "message": "数据库已更新", "summary": db.summary()})
    except yaml.YAMLError as e:
        return jsonify({"ok": False, "message": f"YAML 格式错误: {e}"})


# ─── API: 简历上传导入 ────────────────────────────────────────────

@app.route("/api/upload", methods=["POST"])
def api_upload():
    u = current_user()
    if not u:
        return jsonify({"ok": False, "message": "请先创建用户"})
    if "file" not in request.files:
        return jsonify({"ok": False, "message": "未选择文件"})
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"ok": False, "message": "文件名为空"})

    import tempfile
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix)
    file.save(tmp.name)
    tmp.close()

    cfg = load_config()
    if not cfg["api_key"]:
        return jsonify({"ok": False, "message": "请先配置 API Key"})

    try:
        result = import_resume(cfg, tmp.name, user=u)
    except Exception as e:
        result = {"success": False, "message": f"AI 解析出错: {e}"}
    os.unlink(tmp.name)
    return jsonify(result)


@app.route("/api/upload/stream", methods=["POST"])
def api_upload_stream():
    """SSE 流式上传（保留兼容）。"""
    u = current_user()
    if not u:
        return jsonify({"ok": False, "message": "请先创建用户"})
    if "file" not in request.files:
        return jsonify({"ok": False, "message": "未选择文件"})
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"ok": False, "message": "文件名为空"})

    import tempfile
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix)
    file.save(tmp.name)
    tmp.close()

    cfg = load_config()
    if not cfg["api_key"]:
        os.unlink(tmp.name)
        return jsonify({"ok": False, "message": "请先配置 API Key"})

    from core import import_resume_stream

    def generate():
        try:
            for event in import_resume_stream(cfg, tmp.name, user=u):
                yield event
                yield ": hb\n"
        except Exception as e:
            import traceback as _tb
            detail = _tb.format_exc()
            yield f"data: {json.dumps({'error': str(e), 'traceback': detail})}\n\n"
        os.unlink(tmp.name)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ─── 轮询式任务管理器（绕过 WebKit 60s 超时） ──────────────────────────
import threading
import uuid

_tasks = {}  # task_id → {events: [...], done: bool, error: str|None}


def _start_task(generator):
    """启动后台任务，返回 task_id。前端通过 /poll/<id> 拉取进度。"""
    task_id = uuid.uuid4().hex
    _tasks[task_id] = {"events": [], "done": False, "error": None}

    def _run():
        try:
            for event in generator:
                _tasks[task_id]["events"].append(event)
        except Exception as e:
            import traceback as _tb
            _tasks[task_id]["error"] = f"{e}\n{_tb.format_exc()}"
        _tasks[task_id]["done"] = True

    threading.Thread(target=_run, daemon=True).start()
    return task_id


@app.route("/api/poll/<task_id>", methods=["GET"])
def api_poll_status(task_id):
    """获取后台任务的最新事件。"""
    task = _tasks.get(task_id)
    if not task:
        return jsonify({"ok": False, "message": "任务不存在或已过期"})

    events = task["events"][:]
    task["events"] = []

    return jsonify({
        "ok": True,
        "done": task["done"],
        "error": task["error"],
        "events": events,
    })


# ─── 上传（轮询） ──────────────────────────────────────────────────

@app.route("/api/upload/poll", methods=["POST"])
def api_upload_poll_start():
    u = current_user()
    if not u:
        return jsonify({"ok": False, "message": "请先创建用户"})
    if "file" not in request.files:
        return jsonify({"ok": False, "message": "未选择文件"})
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"ok": False, "message": "文件名为空"})

    import tempfile
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix)
    file.save(tmp.name)
    tmp.close()

    cfg = load_config()
    if not cfg["api_key"]:
        os.unlink(tmp.name)
        return jsonify({"ok": False, "message": "请先配置 API Key"})

    from core import import_resume_stream

    def _run():
        try:
            for event in import_resume_stream(cfg, tmp.name, user=u):
                yield event
        finally:
            os.unlink(tmp.name)

    task_id = _start_task(_run())
    return jsonify({"ok": True, "task_id": task_id})


# ─── 定制生成（轮询） ──────────────────────────────────────────────

@app.route("/api/tailor/poll", methods=["POST"])
def api_tailor_poll_start():
    u = current_user()
    if not u:
        return jsonify({"ok": False, "message": "请先创建用户"})

    cfg = load_config()
    if not cfg["api_key"]:
        return jsonify({"ok": False, "message": "请先配置 API Key"})

    data = request.json
    jd_text = data.get("jd", "").strip()
    if not jd_text:
        return jsonify({"ok": False, "message": "请输入 JD 内容"})

    db = ResumeDatabase(u)
    if not db.exists():
        return jsonify({"ok": False, "message": "简历数据库不存在，请先上传或对话录入"})
    db.load()

    from core import tailor_stream

    task_id = _start_task(tailor_stream(cfg, jd_text, db.to_yaml_string(), u))
    return jsonify({"ok": True, "task_id": task_id})


# ─── 面试准备（轮询） ──────────────────────────────────────────────

@app.route("/api/interview-prep/poll", methods=["POST"])
def api_interview_prep_poll_start():
    u = current_user()
    if not u:
        return jsonify({"ok": False, "message": "请先选择用户"})

    cfg = load_config()
    if not cfg["api_key"]:
        return jsonify({"ok": False, "message": "请先配置 API Key"})

    data = request.json
    jd_text = data.get("jd", "").strip()
    if not jd_text:
        return jsonify({"ok": False, "message": "请输入 JD 内容"})

    db = ResumeDatabase(u)
    if not db.exists():
        return jsonify({"ok": False, "message": "简历数据库不存在"})
    db.load()

    from core import interview_prep_stream

    task_id = _start_task(interview_prep_stream(cfg, jd_text, db.to_yaml_string()))
    return jsonify({"ok": True, "task_id": task_id})


# ─── API: 对话 ────────────────────────────────────────────────────

@app.route("/api/chat/history", methods=["GET"])
def api_chat_history():
    u = current_user()
    if not u:
        return jsonify({"messages": []})
    return jsonify({"messages": load_chat_history(u)})


@app.route("/api/chat/send", methods=["POST"])
def api_chat_send():
    u = current_user()
    if not u:
        return jsonify({"ok": False, "message": "请先创建用户"})

    cfg = load_config()
    if not cfg["api_key"]:
        return jsonify({"ok": False, "message": "请先配置 API Key"})

    data = request.json
    user_msg = data.get("message", "").strip()
    if not user_msg:
        return jsonify({"ok": False, "message": "消息为空"})

    # 从持久化存储加载聊天记录
    messages = load_chat_history(u)

    # 检查是否结束
    if user_msg.lower() in ("完成", "done", "finish"):
        result = chat_extract_yaml(cfg, messages, user=u)
        if result["success"]:
            save_chat_history(u, [])  # 清空聊天记录
            return jsonify({
                "ok": True, "finished": True,
                "message": "✅ 简历数据库已保存！",
                "summary": result.get("summary", {}),
            })
        return jsonify({"ok": False, "message": result["message"], "finished": True})

    messages.append({"role": "user", "content": user_msg})

    def generate():
        client = AIClient(cfg)
        full_reply = ""
        try:
            for token in client.chat_stream(CHAT_SYSTEM_PROMPT, messages):
                full_reply += token
                yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        messages.append({"role": "assistant", "content": full_reply})
        save_chat_history(u, messages)
        yield f"data: {json.dumps({'done': True})}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@app.route("/api/chat/reset", methods=["POST"])
def api_chat_reset():
    u = current_user()
    if u:
        save_chat_history(u, [])
    return jsonify({"ok": True})


# ─── API: JD 管理 ──────────────────────────────────────────────────

@app.route("/api/jds", methods=["GET"])
def api_list_jds():
    u = current_user()
    if not u:
        return jsonify({"jds": []})
    return jsonify({"jds": list_jds(u)})


@app.route("/api/jds/save", methods=["POST"])
def api_save_jd():
    u = current_user()
    if not u:
        return jsonify({"ok": False, "message": "请先选择用户"})
    data = request.json
    name = data.get("name", "").strip()
    content = data.get("content", "").strip()
    if not name or not content:
        return jsonify({"ok": False, "message": "名称和内容不能为空"})
    save_jd(u, name, content)
    return jsonify({"ok": True, "message": "JD 已保存"})


@app.route("/api/jds/get", methods=["POST"])
def api_get_jd():
    u = current_user()
    data = request.json
    name = data.get("name", "").strip()
    content = get_jd(u, name) if u else ""
    return jsonify({"ok": True, "content": content})


# ─── API: 定制生成 ──────────────────────────────────────────────────

@app.route("/api/tailor", methods=["POST"])
def api_tailor():
    u = current_user()
    if not u:
        return jsonify({"ok": False, "message": "请先创建用户"})

    cfg = load_config()
    if not cfg["api_key"]:
        return jsonify({"ok": False, "message": "请先配置 API Key"})

    data = request.json
    jd_text = data.get("jd", "").strip()
    if not jd_text:
        return jsonify({"ok": False, "message": "请输入 JD 内容"})

    db = ResumeDatabase(u)
    if not db.exists():
        return jsonify({"ok": False, "message": "简历数据库不存在，请先上传或对话录入"})
    db.load()

    prompt_path = RESOURCE_DIR / "prompts" / "system_prompt.md"
    if prompt_path.exists():
        prompt_template = prompt_path.read_text(encoding="utf-8")
    else:
        prompt_template = "{jd_text}\n\n{master_yaml}"

    client = AIClient(cfg)
    try:
        typst_code = client.tailor_pipeline(jd_text, db.to_yaml_string(), prompt_template)
    except Exception as e:
        return jsonify({"ok": False, "message": f"AI 调用失败: {e}"})

    typst_code = typst_code.strip()
    for prefix in ["```typst", "```"]:
        if typst_code.startswith(prefix):
            typst_code = typst_code[len(prefix):].strip()
    if typst_code.endswith("```"):
        typst_code = typst_code[:-3].strip()
    typst_code = _ensure_typst_import(typst_code)
    typst_code = _patch_typst_metadata(typst_code)

    compiler = TypstCompiler(u)
    pdf_path, ok, msg = compiler.compile(typst_code, "tailored_cv")

    return jsonify({
        "ok": ok,
        "message": "PDF 生成成功" if ok else msg,
        "pdf_url": f"/outputs/{pdf_path.name}" if ok else None,
        "typst_code": typst_code,
        "pdf_name": pdf_path.name if ok else None,
    })


@app.route("/api/compile", methods=["POST"])
def api_compile():
    """重新编译编辑后的 Typst 代码"""
    u = current_user()
    if not u:
        return jsonify({"ok": False, "message": "请先选择用户"})

    data = request.json
    typst_code = data.get("code", "").strip()
    if not typst_code:
        return jsonify({"ok": False, "message": "Typst 代码为空"})

    typst_code = _ensure_typst_import(typst_code)
    typst_code = _patch_typst_metadata(typst_code)
    compiler = TypstCompiler(u)
    pdf_path, ok, msg = compiler.compile(typst_code, "tailored_cv")

    return jsonify({
        "ok": ok,
        "message": "PDF 生成成功" if ok else msg,
        "pdf_url": f"/outputs/{pdf_path.name}" if ok else None,
        "pdf_name": pdf_path.name if ok else None,
    })


# ─── API: 输出 ──────────────────────────────────────────────────────

@app.route("/outputs/<path:filename>")
def download_output(filename):
    u = current_user()
    from core import get_user_outputs
    filepath = get_user_outputs(u) / filename
    if filepath.exists():
        return send_file(filepath)
    return "File not found", 404


@app.route("/api/outputs", methods=["GET"])
def api_list_outputs():
    u = current_user()
    if not u:
        return jsonify({"files": []})
    return jsonify({"files": list_outputs(u)})


@app.route("/api/outputs/source", methods=["GET"])
def api_output_source():
    """获取指定输出文件的 Typst 源码，用于历史记录回传编辑器。"""
    u = current_user()
    name = request.args.get("name", "")
    if not u or not name:
        return jsonify({"ok": False, "message": "缺少参数"})
    from core import get_user_outputs
    typ_name = name.replace(".pdf", ".typ")
    filepath = get_user_outputs(u) / typ_name
    if filepath.exists():
        return jsonify({"ok": True, "content": filepath.read_text(encoding="utf-8")})
    return jsonify({"ok": False, "message": "源码文件不存在"})


@app.route("/api/interview-prep/stream", methods=["POST"])
def api_interview_prep_stream():
    """SSE streaming version — 实时推送 token，避免长回复超时。"""
    u = current_user()
    if not u:
        return jsonify({"ok": False, "message": "请先选择用户"})

    cfg = load_config()
    if not cfg["api_key"]:
        return jsonify({"ok": False, "message": "请先配置 API Key"})

    data = request.json
    jd_text = data.get("jd", "").strip()
    if not jd_text:
        return jsonify({"ok": False, "message": "请输入 JD 内容"})

    db = ResumeDatabase(u)
    if not db.exists():
        return jsonify({"ok": False, "message": "简历数据库不存在"})
    db.load()

    client = AIClient(cfg)
    system_prompt = INTERVIEW_PREP_PROMPT.replace("{jd_text}", jd_text).replace("{master_yaml}", db.to_yaml_string())

    def generate():
        full = ""
        try:
            for token in client.chat_long_stream(system_prompt, "请根据以上 JD 和简历数据库，输出面试准备分析报告（JSON 格式）。"):
                full += token
                yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return
        try:
            cleaned = _clean_code_fence(full, "json")
            data_parsed = json.loads(cleaned)
            yield f"data: {json.dumps({'done': True, 'data': data_parsed})}\n\n"
        except json.JSONDecodeError:
            yield f"data: {json.dumps({'done': True, 'raw': full, 'parse_error': True})}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


# ─── API: 系统 ──────────────────────────────────────────────────────

@app.route("/api/system/check", methods=["GET"])
def api_system_check():
    from core import check_typst_available
    return jsonify({
        "typst": check_typst_available(),
        "python_version": __import__("sys").version.split()[0],
    })


@app.route("/api/system/install-typst", methods=["POST"])
def api_install_typst():
    from core import install_typst
    ok, msg = install_typst()
    return jsonify({"ok": ok, "message": msg})


# ─── 启动 ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════╗
║   🎯 AI Resume Tailoring Agent       ║
║   打开浏览器访问: http://localhost:8080 ║
╚══════════════════════════════════════╝
""")
    app.run(debug=True, host="127.0.0.1", port=8080)
