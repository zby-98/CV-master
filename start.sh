#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"

# 激活虚拟环境
if [ -f "$DIR/venv/bin/activate" ]; then
  source "$DIR/venv/bin/activate"
else
  echo "请先运行 ./install/setup.sh 安装环境"
  exit 1
fi

# 检查配置
if [ ! -f "$DIR/.env.yaml" ]; then
  echo "请先配置 .env.yaml（参考 install/.env.yaml.example）"
  exit 1
fi

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   🎯 AI Resume Tailoring Agent       ║"
echo "║   打开浏览器访问: http://localhost:8080 ║"
echo "╚══════════════════════════════════════╝"
echo ""

cd "$DIR"
python3 app.py
