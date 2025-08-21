# 주차 쿠폰 자동화 시스템 (PCA_abcd) - Qwen Code Context

## 프로젝트 개요

이 시스템은 주차 정산 웹사이트에 자동으로 로그인하여 차량번호로 할인 대상 차량을 조회하고, 각 매장의 정책에 맞는 최적의 할인 쿠폰을 적용하는 자동화 시스템입니다. 총 5개의 매장(A, B, C, D, E)을 지원하며, Clean Architecture 원칙을 기반으로 설계되어 확장성과 유지보수성이 뛰어납니다.

### 주요 특징
- **멀티 매장 지원**: 5개의 서로 다른 주차 매장(A, B, C, D, E) 지원
- **웹 자동화**: Playwright를 사용한 브라우저 자동화
- **동적 쿠폰 계산**: 각 매장의 정책에 따른 최적의 쿠폰 자동 계산
- **AWS Lambda 배포**: 컨테이너화된 Lambda 환경에 최적화
- **구조화된 로깅**: JSON 형식의 구조화된 로깅 시스템
- **텔레그램 알림**: 실패 시 자동 텔레그램 알림

## 아키텍처

### 클린 아키텍처 구조

```
parking_automation/
├── core/                           # 핵심 도메인 로직
│   ├── domain/                     # 도메인 계층
│   │   ├── models/                 # 도메인 모델 (Vehicle, Coupon, Store 등)
│   │   ├── repositories/           # 리포지토리 인터페이스
│   │   └── rules/                  # 할인 규칙
│   └── application/                # 애플리케이션 계층
│       ├── use_cases/              # 유스케이스 (ApplyCouponUseCase)
│       └── dto/                    # 데이터 전송 객체
├── infrastructure/                 # 인프라스트럭처 계층
│   ├── config/                     # 설정 관리
│   ├── web_automation/             # 웹 자동화 (Playwright)
│   │   └── store_crawlers/         # 매장별 크롤러 구현
│   ├── notifications/              # 알림 시스템
│   ├── logging/                    # 로깅 시스템
│   └── factories/                  # 팩토리 패턴
├── interfaces/                     # 인터페이스 계층
│   └── api/                        # API 엔드포인트 (Lambda)
├── shared/                         # 공유 컴포넌트
│   ├── exceptions/                 # 커스텀 예외
│   └── utils/                      # 유틸리티
├── stores/                         # 매장 라우팅
└── tests/                          # 테스트
```

### 주요 기술 스택
- **Python 3.12**: 주요 프로그래밍 언어
- **Playwright**: 웹 자동화 프레임워크
- **AWS Lambda**: 서버리스 배포 대상
- **PyYAML**: 설정 관리
- **Loguru**: 구조화된 로깅
- **Docker**: 컨테이너화

## 핵심 구성 요소

### 1. 도메인 모델 (core/domain/models/)
- **Vehicle**: 차량 정보 모델
- **Coupon**: 쿠폰 엔티티 (FREE, PAID, WEEKEND 타입)
- **Store**: 매장 설정 및 정책
- **DiscountPolicy**: 할인 정책 및 동적 계산 알고리즘

### 2. 웹 자동화 (infrastructure/web_automation/)
- **BaseCrawler**: 모든 매장 크롤러의 베이스 클래스
- **StoreCrawlers**: 매장별 구현 (AStoreCrawler, BStoreCrawler 등)
- **각 매장 크롤러 주요 메서드**:
  - `login()`: 웹사이트 로그인
  - `search_vehicle()`: 차량 검색
  - `get_coupon_history()`: 쿠폰 이력 조회
  - `apply_coupons()`: 쿠폰 적용
  - `cleanup()`: 브라우저 리소스 정리

### 3. 설정 관리 (infrastructure/config/)
- **ConfigManager**: 설정 파일 로딩 및 관리
- **매장별 설정 파일**: `infrastructure/config/store_configs/{a-e}_store_config.yaml`
- **설정 항목**:
  - 매장 기본 정보 (ID, 이름, 웹사이트 URL)
  - 로그인 정보 (사용자명, 비밀번호)
  - 쿠폰 설정 (타입, 시간, 우선순위)
  - 할인 정책 (평일/주말 목표 시간)
  - 웹 셀렉터 (로그인, 검색, 쿠폰 관련 요소 선택자)

### 4. 애플리케이션 계층 (core/application/)
- **ApplyCouponUseCase**: 주요 비즈니스 로직
  1. 로그인
  2. 차량 검색
  3. 쿠폰 이력 조회
  4. 할인 계산
  5. 쿠폰 적용

### 5. 팩토리 패턴 (infrastructure/factories/)
- **AutomationFactory**: 컴포넌트 생성 팩토리
  - Logger, NotificationService, StoreRepository, DiscountCalculator 생성

## 주요 워크플로우

1. **Lambda 요청 수신**: `lambda_handler`에서 요청 파라미터 파싱
2. **팩토리 생성**: `AutomationFactory`를 통해 필요한 컴포넌트 생성
3. **유스케이스 실행**: `ApplyCouponUseCase.execute()` 호출
4. **웹 자동화**: 매장별 크롤러를 통한 실제 웹사이트 조작
5. **쿠폰 계산**: `DiscountCalculator`를 통한 최적 쿠폰 계산
6. **쿠폰 적용**: 계산된 쿠폰을 웹사이트에 적용
7. **결과 반환**: 성공/실패 여부와 함께 응답 반환

## 배포 구조

### Docker 컨테이너
- **베이스 이미지**: AWS Lambda Python 3.12
- **시스템 라이브러리**: Playwright 실행을 위한 최소한의 라이브러리
- **Playwright 브라우저**: Chromium 브라우저 설치
- **Lambda 핸들러**: `interfaces.api.lambda_handler.lambda_handler`

### Lambda 함수
- 각 매장별로 독립된 Lambda 함수 존재 (lambda_a.py, lambda_b.py 등)
- 공통 엔트리포인트: `lambda_handler.py`

## 개발 및 테스트

### 개발 환경 설정
1. 의존성 설치: `pip install -r requirements.txt`
2. Playwright 브라우저 설치: `playwright install chromium`

### 테스트 실행
- 빠른 테스트: `python tests/e2e/quick_d_store_test.py`
- 인터랙티브 테스트: `python tests/e2e/run_d_store_crawler_direct.py`
- 전체 E2E 테스트: `run_d_store_tests.sh`

### 설정 파일
각 매장은 독립된 YAML 설정 파일을 사용:
- `infrastructure/config/store_configs/a_store_config.yaml`
- `infrastructure/config/store_configs/b_store_config.yaml`
- `infrastructure/config/store_configs/c_store_config.yaml`
- `infrastructure/config/store_configs/d_store_config.yaml`
- `infrastructure/config/store_configs/e_store_config.yaml`

## 새로운 매장 추가 방법

1. **설정 파일 생성**: `infrastructure/config/store_configs/{new}_store_config.yaml`
2. **크롤러 구현**: `infrastructure/web_automation/store_crawlers/{new}_store_crawler.py`
3. **라우팅 등록**: `stores/store_router.py`에 새 매장 추가
4. **Lambda 핸들러 생성**: `interfaces/api/lambda_{new}.py`
5. **팩토리 등록**: `infrastructure/factories/automation_factory.py`에 새 매장 추가
6. **테스트 작성**: 새 매장에 대한 테스트 케이스 작성

## 성능 최적화

- **브라우저 재사용**: Lambda 컨테이너 재사용 시 브라우저 인스턴스 공유
- **설정 캐싱**: 설정 파일 및 로거 인스턴스 캐싱
- **Lambda 최적화**: 컨테이너 재사용을 위한 싱글톤 패턴 적용