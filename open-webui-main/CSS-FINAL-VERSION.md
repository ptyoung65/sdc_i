# CSS 최종 확정 버전 (2025-10-31)

## 📌 개요

이 문서는 Open WebUI의 CSS 최종 확정 버전을 설명합니다. 이 CSS는 깔끔한 UI/UX를 제공하며, 향후 빌드 시에도 자동으로 복원되도록 설정되어 있습니다.

## 🎨 확정된 CSS 특징

- **깔끔한 흰색 배경** (라이트 모드)
- **중앙 정렬된 로그인 폼**
- **둥근 버튼** (border-radius: 9999px)
- **부드러운 UI 요소**
- **일관된 디자인 시스템**

## 📦 백업 위치

### 전체 빌드 백업
```
/home/chatpro/open-webui-main/build-final-css-confirmed.tar.gz
```

### CSS 전용 백업
```
/home/chatpro/open-webui-main/build-final-css-assets/
```

### 이전 백업 (참조용)
```
/home/chatpro/build.tar.gz (2025-10-25)
/home/chatpro/open-webui-main/build_css_backup/
```

## 📝 확정된 CSS 파일 목록

| 파일명 | 크기 | 용도 |
|--------|------|------|
| **0.vCeBmQ_B.css** | 242KB | 메인 CSS (가장 중요) |
| Toaster.DQwrSZtH.css | 13KB | 토스트 알림 |
| katex.e3LZ4nfp.css | 29KB | 수식 렌더링 |
| leaflet.CIGW-MKW.css | 16KB | 지도 컴포넌트 |
| 2.BsgEF8AX.css | 2.5KB | 페이지 스타일 |
| Messages.BAI5BzhU.css | 1.3KB | 메시지 컴포넌트 |
| Collapsible.BSTcku12.css | 1.3KB | 접기/펼치기 |
| VirtualList.Behhsett.css | 278B | 가상 리스트 |
| Modal.CyLKLEmt.css | 185B | 모달 다이얼로그 |
| 42.DUP86x5U.css | 169B | 페이지 42 |
| Skeleton.Cr25vAl_.css | 166B | 로딩 스켈레톤 |
| 22.MBtznMuN.css | 188B | 페이지 22 |
| 31.wEbTgpRj.css | 130B | 페이지 31 |
| RichTextInput.Bx2lu9jm.css | 119B | 리치 텍스트 입력 |
| ConfirmDialog.kaSBQ3kP.css | 102B | 확인 다이얼로그 |

## 🔧 빌드 시 CSS 자동 복원

### 자동 복원 설정 (권장)

`package.json`에 이미 설정되어 있습니다:

```json
"scripts": {
  "build": "npm run pyodide:fetch && vite build && ./restore-css-after-build.sh"
}
```

**사용법:**
```bash
npm run build
```

위 명령어를 실행하면:
1. 일반 빌드 수행 (`vite build`)
2. 자동으로 확정된 CSS로 복원 (`restore-css-after-build.sh`)

### 수동 복원

빌드 후 CSS만 복원하려면:

```bash
./restore-css-after-build.sh
```

### CSS 변경 없이 빌드 (원본 빌드)

CSS 자동 복원 없이 순수 빌드만 원하는 경우:

```bash
npm run build:original
```

## 🚀 배포 프로세스

### 1. 코드 수정 후 빌드
```bash
# 소스 코드 수정 (src/ 디렉토리)
npm run build  # CSS 자동 복원 포함
```

### 2. 컨테이너 재시작
```bash
podman stop sdc-open-webui
podman start sdc-open-webui
```

### 3. 확인
```bash
curl -s -o /dev/null -w "%{http_code}" http://192.168.122.177:3000/
# 응답: 200

# 또는 브라우저에서 확인
firefox http://192.168.122.177:3000/
```

## ⚠️ 중요 사항

### CSS 변경 금지
- `build/_app/immutable/assets/` 디렉토리를 **절대 수동으로 수정하지 마세요**
- 빌드 시 자동으로 확정된 CSS로 복원됩니다

### CSS 수정이 필요한 경우
CSS를 실제로 변경해야 한다면:

1. **소스 파일 수정** (`src/` 디렉토리의 Svelte 파일)
2. **빌드 (CSS 복원 비활성화):**
   ```bash
   npm run build:original
   ```
3. **새 CSS 확인 및 만족하면:**
   ```bash
   # CSS 백업 디렉토리 업데이트
   rm -rf build-final-css-assets/
   mkdir -p build-final-css-assets
   cp -r build/_app/immutable/assets/ build-final-css-assets/

   # 전체 빌드 백업 업데이트
   tar -czf build-final-css-confirmed.tar.gz build/
   ```
4. **다시 자동 복원 활성화** (이미 설정됨)

### 백업 확인
정기적으로 백업이 존재하는지 확인:

```bash
ls -lh build-final-css-confirmed.tar.gz
ls -lh build-final-css-assets/assets/*.css
```

## 📊 CSS 검증

빌드 후 CSS가 제대로 적용되었는지 확인:

```bash
node verify-css-final.cjs
```

또는 Playwright로 시각적 확인:

```bash
npx playwright test verify-css-restored-final.cjs --headed
```

## 🔍 트러블슈팅

### CSS가 이상하게 보이는 경우

1. **수동 CSS 복원:**
   ```bash
   ./restore-css-after-build.sh
   podman restart sdc-open-webui
   ```

2. **전체 빌드 복원:**
   ```bash
   rm -rf build/
   tar -xzf build-final-css-confirmed.tar.gz
   podman restart sdc-open-webui
   ```

3. **CSS 파일 확인:**
   ```bash
   ls -lh build/_app/immutable/assets/0.vCeBmQ_B.css
   # 예상 크기: 242K
   ```

### app.js에서 CSS 참조 확인

```bash
grep "vCeBmQ_B.css" build/_app/immutable/entry/app.BqWdQYeF.js
# 결과가 있어야 함 (CSS 참조 정상)
```

## 📅 버전 히스토리

| 날짜 | 버전 | 변경사항 |
|------|------|----------|
| 2025-10-31 | 1.0 | CSS 최종 확정 (자동 복원 스크립트 추가) |
| 2025-10-25 | 0.9 | 깔끔한 CSS 버전 (백업 생성) |

## 📧 문의

CSS 관련 문제가 발생하면 이 문서를 참조하고, 필요시 백업에서 복원하세요.

---

**마지막 업데이트:** 2025-10-31
**백업 위치:** `/home/chatpro/open-webui-main/build-final-css-confirmed.tar.gz`
**자동 복원 스크립트:** `./restore-css-after-build.sh`
