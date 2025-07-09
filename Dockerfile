# 1. AWS Lambda 공식 베이스 이미지 사용
FROM public.ecr.aws/lambda/python:3.12

# 2. Playwright의 내장 브라우저 실행에 필요한 최소한의 시스템 라이브러리 설치
# (Playwright 공식 문서 및 Amazon Linux 2023 리포지토리 기준 검증 완료)
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
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir playwright==1.40.0

# 4. 모든 사용자가 접근 가능한 공용 경로에 Playwright 브라우저 설치
# 이 환경 변수 설정이 Lambda 런타임 에러를 해결하는 핵심입니다.
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright
RUN playwright install chromium

# 5. 애플리케이션 코드 복사
COPY . ${LAMBDA_TASK_ROOT}/

# 6. Lambda 핸들러 설정
CMD ["interfaces.api.lambda_handler.lambda_handler"]