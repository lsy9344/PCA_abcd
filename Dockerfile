# 1. AWS Lambda 공식 베이스 이미지 사용
FROM public.ecr.aws/lambda/python:3.12

# 2. Playwright의 내장 브라우저 실행에 필요한 최소한의 시스템 라이브러리 설치
# (Playwright 공식 문서 및 커뮤니티 가이드 기반)
RUN dnf install -y \
    alsa-lib \
    atk \
    at-spi2-atk \
    cairo \
    cups-libs \
    dbus-libs \
    gtk3 \
    libXcomposite \
    libXdamage \
    libXfixes \
    libXrandr \
    libXScrnSaver \
    libxkbcommon \
    libxshmfence \
    mesa-libgbm \
    nss \
    pango \
    # 폰트 관련 라이브러리 (스크린샷 깨짐 방지)
     liberation-sans-fonts \
    && dnf clean all

# 3. requirements.txt 복사 및 Python 패키지 설치
COPY requirements.txt ./
# --no-cache-dir 옵션으로 이미지 용량 최적화
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir playwright==1.40.0

# 4. Playwright를 사용하여 Lambda 환경에 맞는 Chromium 브라우저 설치
RUN playwright install chromium

# 5. 애플리케이션 코드 복사
COPY . ${LAMBDA_TASK_ROOT}/

# 6. 환경 변수 설정
ENV PYTHONPATH="${LAMBDA_TASK_ROOT}"
# PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD 변수는 제거하거나 0으로 설정해야 합니다.

# 7. Lambda 핸들러 설정
CMD ["interfaces.api.lambda_handler.lambda_handler"]