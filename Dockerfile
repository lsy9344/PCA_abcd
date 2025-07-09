FROM public.ecr.aws/lambda/python:3.12

# microdnf를 사용한 최소 의존성 설치 (Amazon Linux 2023 호환)
RUN microdnf update -y && \
    microdnf install -y \
        wget \
        tar \
        gzip \
    && microdnf clean all

# Google Chrome 최신 버전 직접 다운로드
RUN wget -O /tmp/google-chrome.rpm "https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm" && \
    rpm -ivh /tmp/google-chrome.rpm --nodeps --force && \
    rm /tmp/google-chrome.rpm

# Chrome 실행에 필요한 최소 라이브러리들을 별도로 다운로드
RUN microdnf install -y \
        nss \
        atk \
        cups-libs \
        libdrm \
        gtk3 \
        libXcomposite \
        libXdamage \
        libXrandr \
        libXss \
        alsa-lib \
    && microdnf clean all

# 🚨 중요: 모든 필수 Python 패키지들 명시적으로 설치
RUN pip install --no-cache-dir \
    PyYAML>=6.0 \
    holidays>=0.34 \
    pydantic>=2.0.0 \
    requests>=2.31.0 \
    boto3>=1.26.0 \
    typing-extensions>=4.5.0 \
    python-dateutil>=2.8.0 \
    pytz>=2023.3

# Python 패키지 설치
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir playwright==1.40.0

# 애플리케이션 코드 복사
COPY . ${LAMBDA_TASK_ROOT}/

# 환경 변수 설정
ENV PYTHONPATH="${LAMBDA_TASK_ROOT}"
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

# Lambda 핸들러 설정
CMD ["lambda_handler.lambda_handler"]