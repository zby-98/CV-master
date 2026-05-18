#!/usr/bin/env bash
# 生成分发包
set -e

DIR="$(cd "$(dirname "$0")/.." && pwd)"
DIST_DIR="$DIR/dist"
PKG_NAME="cv-assistant-$(date +%Y%m%d)"
PKG_PATH="$DIST_DIR/$PKG_NAME"

echo "→ 清理旧包..."
rm -rf "$PKG_PATH" "$DIST_DIR/$PKG_NAME.zip"

echo "→ 复制文件..."
mkdir -p "$PKG_PATH"
cp -R "$DIR"/app.py "$DIR"/core.py "$DIR"/build_resume.py "$PKG_PATH"/
cp -R "$DIR"/start.sh "$PKG_PATH"/
cp -R "$DIR"/.gitignore "$PKG_PATH"/
cp -R "$DIR"/README.md "$PKG_PATH"/
cp -R "$DIR"/prompts "$PKG_PATH"/
cp -R "$DIR"/templates "$PKG_PATH"/
cp -R "$DIR"/fonts "$PKG_PATH"/
cp -R "$DIR"/install "$PKG_PATH"/

echo "→ 打包..."
cd "$DIST_DIR"
zip -r "$PKG_NAME.zip" "$PKG_NAME" -q

echo "→ 清理..."
rm -rf "$PKG_NAME"

echo ""
echo "✓ 分发包已生成："
echo "  $DIST_DIR/$PKG_NAME.zip"
ls -lh "$DIST_DIR/$PKG_NAME.zip"
