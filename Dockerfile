# 1. AWS Lambda 공식 베이스 이미지 사용
FROM public.ecr.aws/lambda/python:3.12

# 2. dnf를 사용하여 필수 유틸리티 설치
RUN dnf install -y wget tar gzip && dnf clean all

# 3. Google Chrome 최신 버전을 다운로드하고, dnf로 설치
# microdnf는 'localinstall'을 지원하지 않으므로 'install' 명령어를 사용합니다.
RUN wget -O /tmp/google-chrome.rpm "https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm" && \
    dnf install -y /tmp/google-chrome.rpm && \
    rm /tmp/google-chrome.rpm

# 4. requirements.txt 복사 및 Python 패키지 설치
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir playwright==1.40.0

# 5. 애플리케이션 코드 복사
COPY . ${LAMBDA_TASK_ROOT}/

# 6. 환경 변수 설정
ENV PYTHONPATH="${LAMBDA_TASK_ROOT}"
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

# 7. Lambda 핸들러 설정
CMD ["interfaces.api.lambda_handler.lambda_handler"]