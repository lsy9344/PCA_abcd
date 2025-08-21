#!/bin/bash

# D 매장 E2E 테스트 실행 스크립트

echo "🚀 D 매장 E2E 테스트 시작..."

# 가상환경 활성화 (필요시)
# source venv/bin/activate

# 필요한 패키지 설치
echo "📦 필요한 패키지 설치 중..."
pip install pytest pytest-asyncio pytest-mock

# Playwright 브라우저 설치 (필요시)
echo "🌐 Playwright 브라우저 설치 중..."
playwright install chromium

# 테스트 실행 옵션들
echo "🧪 테스트 실행 옵션을 선택하세요:"
echo "1. 빠른 헬스체크만 실행"
echo "2. D 매장 전체 E2E 테스트 실행"
echo "3. 특정 테스트 케이스 실행"
echo "4. 상세 로그와 함께 실행"

read -p "선택하세요 (1-4): " choice

case $choice in
    1)
        echo "⚡ 빠른 헬스체크 실행..."
        python -m pytest tests/e2e/test_d_store_crawler.py::test_d_store_quick_health_check -v
        ;;
    2)
        echo "🔄 D 매장 전체 E2E 테스트 실행..."
        python -m pytest tests/e2e/test_d_store_crawler.py -v -m d_store
        ;;
    3)
        echo "사용 가능한 테스트 케이스:"
        python -m pytest tests/e2e/test_d_store_crawler.py --collect-only
        echo ""
        read -p "실행할 테스트 메소드명을 입력하세요: " test_method
        python -m pytest tests/e2e/test_d_store_crawler.py::TestDStoreCrawlerE2E::$test_method -v -s
        ;;
    4)
        echo "📝 상세 로그와 함께 실행..."
        python -m pytest tests/e2e/test_d_store_crawler.py -v -s --tb=long --log-cli-level=DEBUG
        ;;
    *)
        echo "❌ 잘못된 선택입니다."
        exit 1
        ;;
esac

echo "✅ 테스트 완료!"