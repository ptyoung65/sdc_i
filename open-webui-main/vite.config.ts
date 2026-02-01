import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

import { viteStaticCopy } from 'vite-plugin-static-copy';

export default defineConfig({
	plugins: [
		sveltekit(),
		viteStaticCopy({
			targets: [
				{
					src: 'node_modules/onnxruntime-web/dist/*.jsep.*',
					dest: 'wasm'
				},
				{
					// Pyodide 오프라인 캐시를 static/pyodide로 복사
					src: 'offline-cache/pyodide/*',
					dest: 'pyodide'
				}
			]
		})
	],
	server: {
		port: 3000,
		host: '0.0.0.0',
		proxy: {
			'/api': {
				target: 'http://localhost:8080',
				changeOrigin: true
			}
		},
		fs: {
			allow: ['..']
		}
	},
	define: {
		APP_VERSION: JSON.stringify(process.env.npm_package_version),
		APP_BUILD_HASH: JSON.stringify(process.env.APP_BUILD_HASH || 'dev-build')
	},
	// ============================================================================================================
	// ----- [2026-01-31] Source Map 보안 취약점 대응 시작 -----
	// 보안 검토 지적사항: Source Map 파일 유출로 인한 원본 소스코드 노출 위험
	// 조치: 프로덕션 빌드에서 source map 생성 비활성화
	// 변경 전: sourcemap: true (기본값) → 변경 후: sourcemap: false
	// ============================================================================================================
	build: {
		sourcemap: false  // .map 파일 생성 안함 (보안 강화)
	},
	// ----- [2026-01-31] Source Map 보안 취약점 대응 종료 -----
	// ============================================================================================================
	worker: {
		format: 'es'
	},
	optimizeDeps: {
		exclude: ['y-protocols']
	},
	esbuild: {
		pure: []  // Keep console.log for debugging
	}
});
