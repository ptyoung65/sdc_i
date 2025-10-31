#!/bin/bash
#
# CSS 복원 스크립트 - 빌드 후 확정된 CSS로 자동 복원
# 사용법: npm run build 후에 이 스크립트 실행
#

set -e

echo "🎨 CSS 복원 스크립트 시작..."
echo ""

# 백업 디렉토리 확인
CSS_BACKUP_DIR="build-final-css-assets"
BUILD_DIR="build/_app/immutable"

if [ ! -d "$CSS_BACKUP_DIR" ]; then
    echo "❌ 에러: CSS 백업 디렉토리가 없습니다: $CSS_BACKUP_DIR"
    echo "   먼저 CSS를 백업해야 합니다."
    exit 1
fi

if [ ! -d "$BUILD_DIR" ]; then
    echo "❌ 에러: 빌드 디렉토리가 없습니다: $BUILD_DIR"
    echo "   먼저 npm run build를 실행해야 합니다."
    exit 1
fi

echo "📦 빌드된 CSS 파일 정보:"
ls -lh "$BUILD_DIR/assets/"*.css 2>/dev/null | awk '{print "  ", $9, "-", $5}' || echo "  CSS 파일 없음"
echo ""

# CSS assets 백업에서 복원
echo "🔄 확정된 CSS 파일로 교체 중..."
rm -rf "$BUILD_DIR/assets/"
cp -r "$CSS_BACKUP_DIR/assets/" "$BUILD_DIR/assets/"

echo ""
echo "📦 복원된 CSS 파일 정보:"
ls -lh "$BUILD_DIR/assets/"*.css 2>/dev/null | awk '{print "  ", $9, "-", $5}'
echo ""

# app.js에서 CSS 참조 업데이트 (동적으로 최신 파일 찾기)
echo "🔧 app.js에서 CSS 참조 업데이트 중..."

# 최신 app.*.js 파일 찾기
APP_JS=$(find "$BUILD_DIR/entry" -name "app.*.js" -type f | head -1)

if [ -f "$APP_JS" ]; then
    APP_JS_NAME=$(basename "$APP_JS")
    echo "  📄 발견된 app.js: $APP_JS_NAME"

    # 새로운 CSS 파일명 찾기 (빌드 시 생성된 것)
    NEW_CSS=$(grep -o '0\.[A-Za-z0-9_-]*\.css' "$APP_JS" | head -1 || echo "")

    if [ -n "$NEW_CSS" ] && [ "$NEW_CSS" != "0.vCeBmQ_B.css" ]; then
        echo "  변경: $NEW_CSS → 0.vCeBmQ_B.css"
        sed -i "s/$NEW_CSS/0.vCeBmQ_B.css/g" "$APP_JS"
        echo "  ✅ CSS 참조 업데이트 완료"
    else
        echo "  ✅ 이미 올바른 CSS 참조 사용 중 (0.vCeBmQ_B.css)"
    fi
else
    echo "⚠️  경고: app.js 파일을 찾을 수 없습니다"
fi

echo ""
echo "✅ CSS 복원 완료!"
echo ""
echo "📋 다음 단계:"
echo "  1. podman stop sdc-open-webui && podman start sdc-open-webui"
echo "  2. http://192.168.122.177:3000 접속하여 확인"
echo ""
