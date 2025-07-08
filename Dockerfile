# =====================================================================
# 1단계: 빌더 (Builder Stage) - 의존성 설치 전용
# =====================================================================
FROM python:3.11-slim-bookworm AS builder

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_ROOT_USER_ACTION=ignore

# lxml 같은 패키지 빌드에 필요한 시스템 도구 설치
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       libxml2-dev \
       libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Python 가상 환경 생성
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 의존성 파일만 먼저 복사 (Docker 캐시 최적화)
WORKDIR /app
COPY requirements.txt .

# Python 의존성 설치
RUN pip install -r requirements.txt

# Playwright 브라우저 바이너리 설치
RUN playwright install chromium

# =====================================================================
# 2단계: 프로덕션 (Production Stage) - 실제 실행용 최종 이미지
# =====================================================================
FROM python:3.11-slim-bookworm AS production

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH="/home/app/.cache/ms-playwright" \
    PATH="/opt/venv/bin:$PATH"

# Playwright 실행에 필요한 최소한의 시스템 라이브러리 설치
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
       libcups2 libdrm2 libgbm1 libasound2 libatspi2.0-0 libx11-6 \
       libxcomposite1 libxdamage1 libxext6 libxfixes3 libxrandr2 \
       libu2f-udev libvulkan1 \
    && rm -rf /var/lib/apt/lists/*

# 보안을 위한 non-root 사용자 생성
RUN addgroup --system app && adduser --system --gid app app
WORKDIR /home/app
USER app

# 빌더 단계에서 생성된 결과물(가상환경, 브라우저) 복사
COPY --from=builder --chown=app:app /opt/venv /opt/venv
COPY --from=builder --chown=app:app /root/.cache/ms-playwright ${PLAYWRIGHT_BROWSERS_PATH}

# 애플리케이션 소스 코드 복사
COPY --chown=app:app . .

# Lambda 핸들러 설정 (실제 핸들러 경로로 수정하세요)
CMD ["interfaces.api.lambda_handler.lambda_handler"]