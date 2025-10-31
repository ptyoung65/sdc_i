import { loadPyodide, type PyodideInterface } from 'pyodide';

declare global {
	interface Window {
		stdout: string | null;
		stderr: string | null;
		pyodide: PyodideInterface;
		cells: Record<string, CellState>;
		indexURL: string;
	}
}

type CellState = {
	id: string;
	status: 'idle' | 'running' | 'completed' | 'error';
	result: any;
	stdout: string;
	stderr: string;
};

const initializePyodide = async () => {
	// Ensure Pyodide is loaded once and cached in the worker's global scope
	if (!self.pyodide) {
		self.indexURL = '/pyodide/';
		self.stdout = '';
		self.stderr = '';
		self.cells = {};

		self.pyodide = await loadPyodide({
			indexURL: self.indexURL,
			// 완전 오프라인 모드: CDN 사용 금지
			fullStdLib: false,
			packageCacheDir: self.indexURL
		});

		// 오프라인 캐시에 있는 모든 패키지 사전 로드
		// 이렇게 하면 CDN 접근을 완전히 차단할 수 있습니다
		try {
			console.log('[Pyodide] Loading packages from OFFLINE CACHE ONLY');

			// 필수 패키지들을 오프라인 캐시에서만 로드
			// CDN 접근 없이 로컬 캐시만 사용
			const packagesToPreload = [
				'micropip',
				'packaging',
				'numpy',
				'pandas',
				'matplotlib',
				'scipy',
				'scikit-learn',
				'sympy'
			];

			for (const pkg of packagesToPreload) {
				try {
					await self.pyodide.loadPackage(pkg, {
						checkIntegrity: false,
						messageCallback: (msg: string) => {
							console.log(`[Offline Cache] ${pkg}: ${msg}`);
						},
						errorCallback: (msg: string) => {
							console.warn(`[Offline Cache] ${pkg} error: ${msg}`);
						}
					});
				} catch (err) {
					console.warn(`[Offline Cache] Package ${pkg} not available in offline cache:`, err);
				}
			}

			console.log('[Pyodide] Offline cache packages loaded successfully');
		} catch (err) {
			console.error('[Pyodide] Error loading offline cache packages:', err);
		}
	}
};

const executeCode = async (id: string, code: string) => {
	if (!self.pyodide) {
		await initializePyodide();
	}

	// Update the cell state to "running"
	self.cells[id] = {
		id,
		status: 'running',
		result: null,
		stdout: '',
		stderr: ''
	};

	// Redirect stdout/stderr to stream updates
	self.pyodide.setStdout({
		batched: (msg: string) => {
			self.cells[id].stdout += msg;
			self.postMessage({ type: 'stdout', id, message: msg });
		}
	});
	self.pyodide.setStderr({
		batched: (msg: string) => {
			self.cells[id].stderr += msg;
			self.postMessage({ type: 'stderr', id, message: msg });
		}
	});

	try {
		// ❌ CDN 사용 금지: loadPackagesFromImports() 제거
		// ✅ 오프라인 캐시만 사용: 패키지는 initializePyodide()에서 사전 로드됨

		// 코드에서 import 감지하여 로컬 캐시에서만 로드 시도
		const importRegex = /^(?:from|import)\s+(\w+)/gm;
		const imports = [...code.matchAll(importRegex)].map(match => match[1]);

		if (imports.length > 0) {
			self.postMessage({
				type: 'stdout',
				id,
				package: true,
				message: `[Offline Cache] Detected imports: ${imports.join(', ')}`
			});

			// 오프라인 캐시에서만 패키지 로드 시도
			for (const pkg of imports) {
				if (['sys', 'os', 'math', 'random', 'json'].includes(pkg)) {
					// 내장 모듈은 건너뜀
					continue;
				}

				try {
					await self.pyodide.loadPackage(pkg, {
						checkIntegrity: false,
						messageCallback: (msg: string) => {
							self.postMessage({
								type: 'stdout',
								id,
								package: true,
								message: `[Offline Cache] ${pkg}: ${msg}`
							});
						},
						errorCallback: (msg: string) => {
							self.postMessage({
								type: 'stderr',
								id,
								package: true,
								message: `[Offline Cache] ${pkg}: ${msg}`
							});
						}
					});
				} catch (err) {
					// 오프라인 캐시에 없으면 경고만 출력하고 계속 진행
					self.postMessage({
						type: 'stderr',
						id,
						package: true,
						message: `[Offline Cache] Package ${pkg} not found in offline cache. CDN access is BLOCKED.`
					});
				}
			}
		}

		// Execute the Python code
		const result = await self.pyodide.runPythonAsync(code);
		self.cells[id].result = result;
		self.cells[id].status = 'completed';
	} catch (error) {
		self.cells[id].status = 'error';
		self.cells[id].stderr += `\n${error.toString()}`;
	} finally {
		// Notify parent thread when execution completes
		self.postMessage({
			type: 'result',
			id,
			state: self.cells[id]
		});
	}
};

// Handle messages from the main thread
self.onmessage = async (event) => {
	const { type, id, code, ...args } = event.data;

	switch (type) {
		case 'initialize':
			await initializePyodide();
			self.postMessage({ type: 'initialized' });
			break;

		case 'execute':
			if (id && code) {
				await executeCode(id, code);
			}
			break;

		case 'getState':
			self.postMessage({
				type: 'kernelState',
				state: self.cells
			});
			break;

		case 'terminate':
			// Explicitly clear the worker for cleanup
			for (const key in self.cells) delete self.cells[key];
			self.close();
			break;

		default:
			console.error(`Unknown message type: ${type}`);
	}
};
