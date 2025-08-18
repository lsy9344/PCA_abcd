# 매장 어댑터 통합 가이드

## 개요

본 문서는 B매장 크롤러 통합 과정에서 수립된 매장 어댑터 아키텍처 표준화 가이드입니다. 이 가이드를 따라 새로운 매장(C, D, E 등)을 쉽게 추가할 수 있습니다.

## 완료된 작업 요약

### 1. B매장 크롤러 개선 (완료)
- **파일**: `/infrastructure/web_automation/store_crawlers/b_store_crawler.py`
- **주요 수정사항**:
  - `search_vehicle()` 메서드에 **입차일 설정 로직** 추가
  - `entry_date = "2025-07-01"` 고정값으로 설정
  - `test_b_store_ui_2.py`의 100% 동작 로직 반영
  - 상세 로그 메시지 추가

### 2. B매장 어댑터 생성 (완료)
- **파일**: `/adapters/b_store_adapter.py`
- **기능**: 
  - BStoreCrawler를 표준 StoreAdapter 인터페이스로 감싸는 어댑터
  - 문자열 차량번호를 내부적으로 Vehicle 객체로 변환

### 3. StoreAdapter 인터페이스 표준화 (완료)
- **파일**: `/adapters/store_adapter.py`
- **표준 시그니처**:
  ```python
  async def search_vehicle(self, car_number: str) -> bool
  async def get_coupon_history(self, car_number: str) -> CouponHistory
  ```
- **입력 형식**: 4자리 숫자 문자열 (예: "4603")

### 4. 기존 어댑터 업데이트 (완료)
- **D매장**: `/adapters/d_store_adapter.py` - 내부 Vehicle 변환 로직 추가
- **A매장**: `/adapters/a_store_adapter.py` - 내부 Vehicle 변환 로직 추가

### 5. 매장 레지스트리 업데이트 (완료)
- **파일**: `/adapters/store_registry.py`
- **추가사항**:
  - B매장 어댑터 import 및 등록
  - 지원 매장: D, A, B

### 6. E2E 테스트 업데이트 (완료)
- **파일**: `/tests/e2e/test_store_e2e.py`
- **수정사항**:
  - B매장을 테스트 매개변수에 추가: `["D", "A", "B"]`
  - 차량번호를 B매장 테스트용으로 변경: "4603"
  - 모든 매장이 동일한 방식으로 테스트되도록 단순화

---

## 새로운 매장 추가 표준 절차

### 📋 체크리스트: C매장 추가 가이드

다음 단계를 따라 C매장을 시스템에 통합하세요:

#### 1. 크롤러 개발
- [ ] **크롤러 파일 생성**: `/infrastructure/web_automation/store_crawlers/c_store_crawler.py`
- [ ] **BaseCrawler 상속**: `class CStoreCrawler(BaseCrawler, StoreRepository)`
- [ ] **필수 메서드 구현**:
  - [ ] `async def login(self, vehicle: Optional[Vehicle] = None) -> bool`
  - [ ] `async def search_vehicle(self, vehicle: Vehicle) -> bool`
  - [ ] `async def get_coupon_history(self, vehicle: Vehicle) -> CouponHistory`
  - [ ] `async def apply_coupons(self, applications: List[CouponApplication]) -> bool`

#### 2. 어댑터 생성
- [ ] **어댑터 파일 생성**: `/adapters/c_store_adapter.py`
- [ ] **템플릿 사용**:
```python
"""C매장 어댑터"""

from typing import List
from adapters.store_adapter import StoreAdapter
from core.domain.models.vehicle import Vehicle
from core.domain.models.coupon import CouponHistory, CouponApplication
from infrastructure.web_automation.store_crawlers.c_store_crawler import CStoreCrawler


class CStoreAdapter(StoreAdapter):
    """C매장 크롤러를 표준 인터페이스로 감싸는 어댑터"""
    
    def __init__(self, store_config, playwright_config, structured_logger, notification_service=None):
        self.crawler = CStoreCrawler(
            store_config=store_config,
            playwright_config=playwright_config, 
            structured_logger=structured_logger,
            notification_service=notification_service
        )
        self._vehicle = None
    
    async def start(self) -> None:
        """브라우저/컨텍스트 초기화"""
        pass
    
    async def login(self) -> bool:
        """로그인 수행"""
        return await self.crawler.login()
    
    async def search_vehicle(self, car_number: str) -> bool:
        """차량 검색 - 내부적으로 Vehicle 객체로 변환하여 크롤러에 전달"""
        self._vehicle = Vehicle(number=car_number)
        return await self.crawler.search_vehicle(self._vehicle)
    
    async def get_coupon_history(self, car_number: str) -> CouponHistory:
        """쿠폰 이력 조회 - 내부적으로 Vehicle 객체로 변환하여 크롤러에 전달"""
        if not self._vehicle or self._vehicle.number != car_number:
            self._vehicle = Vehicle(number=car_number)
        return await self.crawler.get_coupon_history(self._vehicle)
    
    async def apply_coupons(self, applications: List[CouponApplication]) -> bool:
        """쿠폰 적용"""
        return await self.crawler.apply_coupons(applications)
    
    async def cleanup(self) -> None:
        """리소스 정리"""
        await self.crawler.cleanup()
```

#### 3. 레지스트리 등록
- [ ] **파일 수정**: `/adapters/store_registry.py`
- [ ] **import 추가**:
```python
from adapters.c_store_adapter import CStoreAdapter
```
- [ ] **매장별 어댑터 생성 부분에 추가**:
```python
elif store_id_upper == 'C':
    return CStoreAdapter(
        store_config=store_config,
        playwright_config=playwright_config,
        structured_logger=structured_logger,
        notification_service=notification_service
    )
```
- [ ] **레지스트리에 추가**:
```python
STORE_REGISTRY: Dict[str, Type[StoreAdapter]] = {
    'D': DStoreAdapter,
    'A': AStoreAdapter,
    'B': BStoreAdapter,
    'C': CStoreAdapter  # 추가
}
```

#### 4. E2E 테스트 업데이트
- [ ] **파일 수정**: `/tests/e2e/test_store_e2e.py`
- [ ] **매개변수 추가**:
```python
@pytest.mark.parametrize("store_id", ["D", "A", "B", "C"])  # C 추가
```
- [ ] **테스트 차량번호 확인**: C매장 전용 테스트 차량번호가 있다면 환경변수 또는 조건부 로직 추가

#### 5. 설정 파일 확인
- [ ] **설정 파일 존재 확인**: `/infrastructure/config/store_configs/c_store_config.yaml`
- [ ] **필수 설정 항목**:
  - `store` 정보 (website_url, name 등)
  - `login` 정보 (username, password)
  - `selectors` 정보 (UI 요소 셀렉터)
  - `coupons` 정보 (쿠폰 설정)
  - `policy` 정보 (할인 정책)

---

## 핵심 아키텍처 원칙

### 🎯 **단일 책임 원칙**
- **크롤러**: 웹 자동화 로직만 담당
- **어댑터**: 인터페이스 변환만 담당
- **레지스트리**: 객체 생성 및 관리만 담당

### 🔄 **일관된 데이터 플로우**
```
외부 호출 (str) → 어댑터 (str→Vehicle 변환) → 크롤러 (Vehicle 처리) → 결과 반환
```

### 📝 **표준 인터페이스**
모든 매장 어댑터는 동일한 메서드 시그니처를 구현:
- `search_vehicle(car_number: str) -> bool`
- `get_coupon_history(car_number: str) -> CouponHistory`
- `apply_coupons(applications: List[CouponApplication]) -> bool`

### 🧪 **테스트 일관성**
- 모든 매장이 동일한 E2E 테스트 로직 사용
- 매장별 특수 로직은 어댑터 내부에서 처리
- 테스트 코드에는 매장별 분기 로직 최소화

---

## 트러블슈팅

### 일반적인 문제들

#### 1. Vehicle 객체 변환 문제
**증상**: 크롤러에서 Vehicle 객체 관련 오류
**해결**: 어댑터에서 `Vehicle(number=car_number)` 정확히 생성 확인

#### 2. 레지스트리 등록 누락
**증상**: `지원하지 않는 매장 ID입니다` 오류
**해결**: 
- `store_registry.py`에 import 추가 확인
- 조건문에 매장 추가 확인
- `STORE_REGISTRY` 딕셔너리에 추가 확인

#### 3. E2E 테스트 실패
**증상**: 새 매장에서 테스트 실패
**해결**:
- 설정 파일 (`c_store_config.yaml`) 존재 확인
- 테스트 차량번호가 해당 매장에서 유효한지 확인
- 크롤러의 각 메서드가 올바르게 구현되었는지 확인

---

## 베스트 프랙티스

### ✅ **DO (권장사항)**
- 어댑터에서만 타입 변환 처리
- 크롤러에서는 도메인 객체(Vehicle) 사용
- 모든 매장이 동일한 인터페이스 준수
- 상세한 로그 메시지 추가
- 에러 처리를 각 레이어에서 적절히 수행

### ❌ **DON'T (지양사항)**
- 인터페이스에 Union 타입 사용
- 테스트 코드에 매장별 특수 로직 추가
- 크롤러에서 직접 문자열 처리
- 레지스트리에 비즈니스 로직 포함
- 하드코딩된 설정값 사용

---

## 작업 완료 확인

다음 명령어로 새 매장이 올바르게 통합되었는지 확인:

```bash
# E2E 테스트 실행 (C매장 포함)
python -m pytest tests/e2e/test_store_e2e.py::test_store_end_to_end[C] -v

# 전체 매장 E2E 테스트
python -m pytest tests/e2e/test_store_e2e.py -v

# 레지스트리 확인
python -c "from adapters.store_registry import get_supported_stores; print(get_supported_stores())"
```

이 가이드를 따라 C매장을 추가하면 기존 B매장 통합과 동일한 품질과 일관성을 유지할 수 있습니다.