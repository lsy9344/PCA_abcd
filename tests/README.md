# 테스트 아키텍처 가이드

## 핵심 원칙

**테스트는 소스의 퍼블릭 API만 호출한다. DOM/셀렉터 조작 금지. 설정은 공용 로더 사용.**

## 디렉토리 구조

```
tests/
├── e2e/                    # E2E 테스트 (권장)
│   └── test_store_e2e.py  # 모든 매장을 파라미터로 테스트
├── legacy/                 # 레거시 UI 테스트 (사용 금지)
│   └── test_*_ui_legacy.py # 스킵된 레거시 테스트들
└── README.md              # 이 파일
```

## 테스트 실행

```bash
# 전체 E2E 테스트
pytest tests/e2e/test_store_e2e.py -v

# 특정 매장만 테스트
pytest "tests/e2e/test_store_e2e.py::test_store_coupon_flow[D]" -v -s

# 단일 매장 직접 실행 (디버깅용)
python tests/e2e/test_store_e2e.py
```

## 금지 사항

- 브라우저 직접 생성
- 셀렉터/팝업/DOM 조작
- `sys.path` 해킹
- `wait_for_timeout` 고정 대기
- 설정 파일 직접 읽기