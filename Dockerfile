FROM public.ecr.aws/lambda/python:3.12

# 시스템 패키지 설치 (apt-get 사용)
RUN apt-get update && \
    apt-get install -y \
        wget \
        nss \
        atk1.0 \
        libcups2 \
        libgtk-3-0 \
        libxcomposite1 \
        libxcursor1 \
        libxdamage1 \
        libxext6 \
        libxi6 \
        libxrandr2 \
        libxss1 \
        libxtst6 \
        libpango-1.0-0 \
        libasound2 \
        libdrm2 \
        libgbm1 \
        xvfb \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir playwright

# Playwright 브라우저 설치 (chromium)
RUN python -m playwright install chromium

# 앱 코드 복사
COPY . .

# Lambda 핸들러 진입점 지정 (파일명.함수명)
CMD ["lambda_handler.lambda_handler"]
