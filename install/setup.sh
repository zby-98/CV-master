#!/usr/bin/env bash
set -e

echo "========================================"
echo "  AI 简历定制助手 — 环境安装"
echo "========================================"
echo ""

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"

# ─── 检查 Python ─────────────────────────────
echo "→ 检查 Python..."
PYTHON=""
for cmd in python3 python; do
  if command -v $cmd &>/dev/null; then
    ver=$($cmd --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
    major=$(echo "$ver" | cut -d. -f1)
    minor=$(echo "$ver" | cut -d. -f2)
    if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
      PYTHON=$cmd
      echo "  ✓ $cmd $ver"
      break
    fi
  fi
done

if [ -z "$PYTHON" ]; then
  echo "  ✗ 需要 Python 3.10+，请先安装"
  echo "    macOS: brew install python@3.12"
  echo "    官网: https://www.python.org/downloads/"
  exit 1
fi

# ─── 创建虚拟环境 ─────────────────────────────
VENV_DIR="$PROJECT_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
  echo ""
  echo "→ 创建虚拟环境..."
  $PYTHON -m venv "$VENV_DIR"
  echo "  ✓ venv 已创建"
else
  echo ""
  echo "→ 虚拟环境已存在"
fi

source "$VENV_DIR/bin/activate"

# ─── 安装依赖 ────────────────────────────────
echo ""
echo "→ 安装 Python 依赖..."
pip install --upgrade pip -q
pip install -r "$INSTALL_DIR/requirements.txt" -q
echo "  ✓ 依赖安装完成"

# ─── 检查 Typst ──────────────────────────────
echo ""
echo "→ 检查 Typst CLI..."
if command -v typst &>/dev/null; then
  echo "  ✓ typst $(typst --version 2>&1 | head -1)"
else
  echo "  ⚠ Typst CLI 未安装（PDF 编译需要）"
  echo ""
  echo "  macOS 安装："
  echo "    brew install typst"
  echo ""
  echo "  其他系统："
  echo "    https://github.com/typst/typst/releases"
  echo "    下载对应平台的二进制文件，放到 PATH 中"
  echo ""
fi

# ─── 检查配置 ────────────────────────────────
echo ""
echo "→ 检查配置文件..."
CONFIG_FILE="$PROJECT_DIR/.env.yaml"
if [ ! -f "$CONFIG_FILE" ]; then
  cp "$INSTALL_DIR/.env.yaml.example" "$CONFIG_FILE"
  echo "  ⚠ 已从模板创建 .env.yaml，请编辑填入你的 API 密钥："
  echo ""
  echo "    vim .env.yaml"
  echo ""
  echo "  API 获取方式（豆包/火山引擎）："
  echo "    1. 访问 https://console.volcengine.com/ark"
  echo "    2. 创建 API Key"
  echo "    3. 创建推理接入点，选择 doubao-seed-2.0-pro 模型"
  echo "    4. 将 API Key 和接入点 ID 填入 .env.yaml"
  echo ""
  echo "  如果用其他兼容 OpenAI 的 API（DeepSeek 等），修改 base_url 和 model 即可"
else
  echo "  ✓ .env.yaml 已存在"
fi

# ─── 完成 ────────────────────────────────────
echo ""
echo "========================================"
echo "  安装完成！"
echo "========================================"
echo ""
echo "  启动方式："
echo "    ./start.sh"
echo ""
echo "  然后打开浏览器访问："
echo "    http://localhost:8080"
echo ""
