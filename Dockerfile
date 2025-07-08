FROM public.ecr.aws/lambda/python:3.9

# 기본 패키지 설치
RUN yum update -y && yum install -y wget && yum clean all

# 최신 Chrome 다운로드
RUN wget -O /tmp/google-chrome.rpm "https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm" && \
    yum localinstall -y /tmp/google-chrome.rpm && \
    rm /tmp/google-chrome.rpm

# 필수 파이썬 패키지 설치
RUN pip install --no-cache-dir \
    PyYAML>=6.0 \
    holidays>=0.34 \
    pydantic>=2.0.0 \
    requests>=2.31.0 \
    boto3>=1.26.0 \
    typing-extensions>=4.5.0 \
    python-dateutil>=2.8.0 \
    pytz>=2023.3

# Python requirements 설치
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir playwright==1.40.0

# 코드 복사
COPY . ${LAMBDA_TASK_ROOT}/

# 환경 변수
ENV PYTHONPATH="${LAMBDA_TASK_ROOT}"
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

# Lambda 핸들러
CMD ["interfaces.api.lambda_handler.lambda_handler"]