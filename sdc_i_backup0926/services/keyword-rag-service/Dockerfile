# Keyword RAG Service Dockerfile - Production Offline Version
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 오프라인 환경: 네트워크 연결 차단
RUN echo 'Acquire::http::Proxy "http://127.0.0.1:65535/";' > /etc/apt/apt.conf.d/99offline && \
    echo 'Acquire::https::Proxy "https://127.0.0.1:65535/";' >> /etc/apt/apt.conf.d/99offline

# 오프라인 Python 패키지 캐시 복사
COPY ./offline-cache/python/ /app/offline-python/

# Keyword RAG에 필요한 requirements.txt 생성 (FastAPI+Pydantic 완전 의존성 포함)
RUN echo "fastapi==0.116.2" > requirements.txt && \
    echo "uvicorn==0.36.0" >> requirements.txt && \
    echo "pydantic==2.11.9" >> requirements.txt && \
    echo "pydantic-core==2.33.2" >> requirements.txt && \
    echo "starlette==0.48.0" >> requirements.txt && \
    echo "anyio==4.10.0" >> requirements.txt && \
    echo "typing_extensions==4.15.0" >> requirements.txt && \
    echo "annotated_types==0.7.0" >> requirements.txt && \
    echo "typing_inspection==0.4.1" >> requirements.txt && \
    echo "sniffio==1.3.1" >> requirements.txt && \
    echo "idna==3.10" >> requirements.txt && \
    echo "h11==0.16.0" >> requirements.txt && \
    echo "click==8.3.0" >> requirements.txt && \
    echo "httpx==0.28.1" >> requirements.txt && \
    echo "elasticsearch==8.11.0" >> requirements.txt && \
    echo "numpy==1.26.4" >> requirements.txt && \
    echo "pandas==2.3.2" >> requirements.txt && \
    echo "scikit-learn==1.3.2" >> requirements.txt && \
    echo "prometheus-client==0.23.1" >> requirements.txt && \
    echo "structlog==25.4.0" >> requirements.txt

# Python 패키지 설치 (완전 오프라인)
ENV PIP_NO_INDEX=1
ENV PIP_FIND_LINKS=/app/offline-python/wheels
ENV PIP_OFFLINE=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
RUN pip install --no-index --find-links /app/offline-python/wheels --no-deps -r requirements.txt || \
    pip install --no-index --find-links /home/chatpro/sdc_i/offline_packages/python_cache/ --no-deps -r requirements.txt

# 애플리케이션 파일 복사
COPY ./services/keyword-rag-service /app/

# 포트 노출
EXPOSE 8011

# 헬스체크 설정
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8011/health || exit 1

# 실행 권한 설정
RUN chmod +x /app/main.py

# 서비스 실행
CMD ["python", "main.py", "--host", "0.0.0.0", "--port", "8011"]