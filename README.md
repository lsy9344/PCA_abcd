# 주차 쿠폰 자동화 시스템

## 📋 개요

주차 정산 웹사이트에 자동으로 로그인하여 차량번호로 할인 대상 차량을 조회하고, 각 매장의 정책에 맞는 최적의 할인 쿠폰을 적용하는 자동화 시스템입니다.

## 🏗️ 아키텍처

### 클린 아키텍처 기반 설계

```
parking_automation/
├── core/                           # 핵심 도메인 로직
│   ├── domain/                     # 도메인 계층
│   │   ├── models/                 # 도메인 모델
│   │   ├── repositories/           # 리포지토리 인터페이스
│   └── application/                # 애플리케이션 계층
│       ├── use_cases/              # 유스케이스
│       └── dto/                    # 데이터 전송 객체
├── infrastructure/                 # 인프라스트럭처 계층
│   ├── config/                     # 설정 관리
│   ├── web_automation/             # 웹 자동화 (Playwright)
│   ├── notifications/              # 알림 시스템
│   ├── logging/                    # 로깅 시스템
│   └── factories/                  # 팩토리 패턴
├── interfaces/                     # 인터페이스 계층
│   ├── api/                        # API 엔드포인트 (Lambda)
│   └── cli/                        # CLI 인터페이스
├── shared/                         # 공유 컴포넌트
│   ├── exceptions/                 # 커스텀 예외
│   └── utils/                      # 유틸리티
└── tests/                          # 테스트
```

### 주요 특징

- **도메인 중심 설계**: 비즈니스 로직이 핵심에 위치
- **의존성 역전**: 인터페이스를 통한 느슨한 결합
- **매장별 독립성**: 각 매장의 설정과 로직이 완전히 분리
- **확장성**: 새로운 매장 추가가 용이
- **테스트 가능성**: 각 계층별 독립적인 테스트 가능

## 🚀 사용법

### CLI 실행

```bash
# A매장 자동화 실행
python interfaces/cli/main.py --store A --vehicle 12가3456

# B매장 자동화 실행 (구현 예정)
python interfaces/cli/main.py --store B --vehicle 12가3456

# 커스텀 설정 디렉토리 사용
python interfaces/cli/main.py --store A --vehicle 12가3456 --config-dir /path/to/config
```

### AWS Lambda 배포

```python
# interfaces/api/lambda_handler.py의 lambda_handler 함수를 Lambda에 배포

# 호출 예시
{
    "store_id": "A",
    "vehicle_number": "12가3456"
}
```

## ⚙️ 설정

### 매장별 설정 파일

각 매장의 설정은 YAML 파일로 관리됩니다:

- `infrastructure/config/store_configs/a_store_config.yaml`
- `infrastructure/config/store_configs/b_store_config.yaml`

### 설정 구조

```yaml
# 매장 기본 정보
store:
  id: "A"
  name: "A매장"
  website_url: "http://example.com"

# 로그인 정보
login:
  username: "your_username"
  password: "your_password"

# 쿠폰 타입 매핑
coupons:
  FREE_1HOUR:
    name: "1시간 무료 쿠폰"
    type: "free"
    duration_minutes: 60
    priority: 0

# 할인 정책
discount_policy:
  weekday:
    target_hours: 3
    max_coupons: 3
  weekend:
    target_hours: 2
    max_coupons: 2

# 웹 셀렉터
selectors:
  login:
    username_input: "#username"
    password_input: "#password"
    login_button: "#login"
```

## 🔧 개발 환경 설정

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. Playwright 브라우저 설치

```bash
playwright install chromium
```

### 3. 설정 파일 구성

매장별 설정 파일을 실제 환경에 맞게 수정하세요.

## 🧪 테스트

```bash
# 단위 테스트 실행
python -m pytest tests/unit/

# 통합 테스트 실행
python -m pytest tests/integration/

# 전체 테스트 실행
python -m pytest
```

## 📊 로깅 및 모니터링

### 구조화된 로깅

모든 로그는 JSON 형태로 구조화되어 저장됩니다:

```
2024-01-01 12:00:00 - store_a - INFO - [A][로그인] 성공 | {"store_id": "A", "step": "login"}
```

### 텔레그램 알림

실패 시 자동으로 텔레그램 알림이 전송됩니다:

```
🚨 쿠폰 자동화 실패 알림 🚨

1. 실패 원인: [차량검색] 검색된 차량이 없습니다.
2. 실패 차량번호: 12가3456
3. 실패 매장: A
4. 실패 시간: 2024/01/01 12:00:00
```

## 🔄 새로운 매장 추가

1. **설정 파일 생성**: `infrastructure/config/store_configs/c_store_config.yaml`
2. **크롤러 구현**: `infrastructure/web_automation/store_crawlers/c_store_crawler.py`
3. **팩토리 등록**: `AutomationFactory`에 새 매장 추가
4. **테스트 작성**: 새 매장에 대한 테스트 케이스 작성

## 📈 성능 최적화

- **브라우저 재사용**: Lambda 컨테이너 재사용 시 브라우저 인스턴스 공유
- **병렬 처리**: 여러 차량 동시 처리 가능
- **캐싱**: 설정 파일 및 로거 인스턴스 캐싱

## 🛡️ 보안

- **설정 분리**: 민감한 정보는 환경변수 또는 AWS Secrets Manager 사용 권장
- **에러 처리**: 상세한 에러 정보는 로그에만 기록, 외부 노출 최소화
- **접근 제어**: Lambda 함수에 적절한 IAM 역할 설정

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 


///테스트
///테스트2