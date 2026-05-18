#!/usr/bin/env bash
# 构建 macOS .app 和 Windows .exe 分发包
# 用法: ./install/build.sh [mac|win|all]
set -e

DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$DIR/build"
DIST_DIR="$DIR/dist"

TYPST_VER="0.12.0"

# ─── 下载 Typst 二进制 ──────────────────────────

download_typst_mac() {
  local dest="$1"
  if [ -f "$dest/typst" ]; then echo "  ✓ typst 已存在"; return; fi
  echo "  → 下载 typst macOS arm64..."
  local url="https://github.com/typst/typst/releases/download/v${TYPST_VER}/typst-aarch64-apple-darwin.tar.xz"
  curl -sL "$url" | tar xJ -C "$dest" typst-aarch64-apple-darwin/typst --strip-components=1
  chmod +x "$dest/typst"
  echo "  ✓ typst 已准备"
}

download_typst_win() {
  local dest="$1"
  if [ -f "$dest/typst.exe" ]; then echo "  ✓ typst 已存在"; return; fi
  echo "  → 下载 typst Windows x64..."
  local url="https://github.com/typst/typst/releases/download/v${TYPST_VER}/typst-x86_64-pc-windows-msvc.zip"
  curl -sL "$url" -o /tmp/typst-win.zip
  unzip -qo /tmp/typst-win.zip -d "$dest"
  rm -f /tmp/typst-win.zip
  echo "  ✓ typst 已准备"
}

# ─── 检查 PyInstaller ───────────────────────────

if ! python3 -c "import PyInstaller" 2>/dev/null; then
  echo "→ 安装 PyInstaller..."
  pip3 install pyinstaller
fi

# ─── 构建 macOS ──────────────────────────────────

build_mac() {
  echo ""
  echo "===== 构建 macOS .app ====="
  mkdir -p "$BUILD_DIR/mac"
  download_typst_mac "$BUILD_DIR/mac"

  # PyInstaller 构建
  cd "$DIR"
  pyinstaller \
    --name "CV-Assistant" \
    --windowed \
    --noconfirm \
    --clean \
    --add-binary "$BUILD_DIR/mac/typst:." \
    --add-data "templates:templates" \
    --add-data "prompts:prompts" \
    --add-data "fonts:fonts" \
    --add-data "install/.env.yaml.example:install" \
    --distpath "$DIST_DIR" \
    --workpath "$BUILD_DIR/pyinstaller" \
    launcher.py

  # 创建 DMG（需要 create-dmg）
  if command -v create-dmg &>/dev/null; then
    echo "  → 创建 DMG..."
    rm -f "$DIST_DIR/CV-Assistant.dmg"
    create-dmg \
      --volname "CV-Assistant" \
      --window-pos 200 120 \
      --window-size 500 300 \
      "$DIST_DIR/CV-Assistant.dmg" \
      "$DIST_DIR/CV-Assistant.app"
    echo "  ✓ $DIST_DIR/CV-Assistant.dmg"
  else
    echo "  ⚠ 未安装 create-dmg，跳过 DMG 打包"
    echo "    安装: brew install create-dmg"
    echo "  ✓ $DIST_DIR/CV-Assistant.app"
  fi
}

# ─── 构建 Windows ─────────────────────────────────

build_win() {
  echo ""
  echo "===== 构建 Windows .exe（交叉编译）====="
  echo "  注意：Windows 打包需要在 Windows 或 wine 环境下运行"
  echo "  在 Windows 上运行: pyinstaller --name CV-Assistant ..."
  echo ""
  echo "  Windows 构建命令（在 Windows 终端执行）："
  echo ""
  cat <<'WINCMD'
  pip install pyinstaller
  # 先下载 typst.exe 放到项目根目录
  pyinstaller ^
    --name "CV-Assistant" ^
    --windowed ^
    --noconfirm ^
    --add-binary "typst.exe;." ^
    --add-data "templates;templates" ^
    --add-data "prompts;prompts" ^
    --add-data "fonts;fonts" ^
    --add-data "install\.env.yaml.example;install" ^
    launcher.py
WINCMD
}

# ─── 入口 ────────────────────────────────────────

case "${1:-mac}" in
  mac)  build_mac ;;
  win)  build_win ;;
  all)  build_mac; build_win ;;
  *)    echo "用法: ./install/build.sh [mac|win|all]"; exit 1 ;;
esac

echo ""
echo "========================================"
echo "  构建完成！"
echo "========================================"
