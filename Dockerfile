FROM public.ecr.aws/lambda/python:3.12

# 필수 리눅스 패키지 설치
RUN yum install -y \
    nss \
    atk \
    cups-libs \
    gtk3 \
    libXcomposite \
    libXcursor \
    libXdamage \
    libXext \
    libXi \
    libXrandr \
    libXScrnSaver \
    libXtst \
    pango \
    alsa-lib \
    libdrm \
    libgbm \
    xorg-x11-server-Xvfb \
    wget \
    && yum clean all

# Python 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir playwright

# Playwright용 chromium 설치
RUN python -m playwright install chromium

COPY . .

CMD ["lambda_handler.lambda_handler"]
