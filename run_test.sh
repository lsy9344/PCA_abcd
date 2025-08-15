#!/bin/bash
# C 매장 테스트 실행 스크립트

echo "🚀 C 매장 테스트 시작..."
echo "📍 가상환경 활성화 중..."

# 가상환경 활성화 및 테스트 실행
source venv/bin/activate && python test_c_store_ui.py

echo "✅ 테스트 완료!"
