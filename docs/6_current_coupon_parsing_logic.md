# 6. 현재 적용된 쿠폰 파싱 및 차감 계산 로직

## 개요

모든 매장에서 쿠폰 적용 시 **현재 이미 적용된 쿠폰을 먼저 확인하고 차감하여 추가로 필요한 쿠폰만 계산**하는 통합 로직입니다.

---

## 핵심 원칙

### 1. 현재 쿠폰 파싱 우선
- 쿠폰 적용 전에 반드시 **현재 적용된 쿠폰 내역을 파싱**
- A, B, C 매장 모두 동일한 방식으로 처리

### 2. 차감 계산 방식
```
추가 필요 할인 시간 = 목표 시간 - 현재 적용된 총 할인 시간
```

### 3. 분 단위 정확 계산
- 시간 단위가 아닌 **분 단위**로 정확히 계산
- 올림 처리로 부족분 없이 커버

---

## 구현 구조

### 1. 공통 유틸리티 (`shared/utils/common_coupon_calculator.py`)

#### **CommonCouponCalculator 클래스**
```python
# 현재 적용된 쿠폰 파싱
parse_applied_coupons(page, coupon_key_mapping, discount_selectors)

# 남은 할인 시간 계산  
calculate_remaining_minutes(target_minutes, coupon_durations, current_history)

# 무료 쿠폰 적용 여부 결정
should_apply_free_coupon(total_free_used, current_free, remaining_minutes, free_coupon_duration)

# 표시용 쿠폰 이름 변환
format_coupon_display_name(coupon_key)
```

#### **StoreConfig 클래스**
```python
# 매장별 설정 반환
get_coupon_config(store_id) -> {
    "coupon_key_mapping": {...},    # 쿠폰 이름 -> 키 매핑
    "coupon_durations": {...},      # 쿠폰별 할인 시간
    "discount_selectors": [...]     # 할인 내역 테이블 셀렉터
}
```

---

## 매장별 설정

### A 매장
```yaml
coupon_key_mapping:
  "30분할인권(무료)": "FREE_COUPON"
  "1시간할인권(유료)": "PAID_COUPON" 
  "1시간주말할인권(유료)": "WEEKEND_COUPON"
  
coupon_durations:
  FREE_COUPON: 60분
  PAID_COUPON: 60분
  WEEKEND_COUPON: 60분
  
discount_selectors: ["#myDcList tr", "#allDcList tr"]
```

### B 매장
```yaml
coupon_key_mapping:
  "무료 1시간할인": "FREE_COUPON"
  "유료 30분할인": "PAID_COUPON"
  
coupon_durations:
  FREE_COUPON: 60분
  PAID_COUPON: 30분
  
discount_selectors: [".discount-list tr", "#discountHistory tr"]
```

### C 매장
```yaml
coupon_key_mapping:
  "무료 2시간할인": "FREE_2HOUR"
  "2시간 무료할인권": "FREE_2HOUR"
  "1시간 유료할인권": "PAID_1HOUR"
  "유료할인": "PAID_1HOUR"
  
coupon_durations:
  FREE_2HOUR: 120분
  PAID_1HOUR: 60분
  
discount_selectors: [
    "#discountHistory tr",
    ".discount-list tr", 
    ".applied-coupons tr",
    "[id*='discount'] tr",
    "[class*='discount'] tr"
  ]
```

---

## 처리 흐름

### 1. 현재 쿠폰 파싱
```python
# C 매장 예시
async def _parse_current_applied_coupons(self):
    store_config = StoreConfig.get_coupon_config("C")
    
    my_history, total_history = await CommonCouponCalculator.parse_applied_coupons(
        self.page,
        store_config["coupon_key_mapping"], 
        store_config["discount_selectors"]
    )
    
    return my_history, total_history
```

### 2. 차감 계산
```python
def _calculate_required_coupons(self, my_history, total_history):
    # 현재 적용된 총 할인 시간 계산 (분 단위)
    current_minutes = 0
    current_minutes += free_current * 120  # 2시간 무료 쿠폰
    current_minutes += paid_1hour_current * 60  # 1시간 유료 쿠폰
    
    # 남은 시간 계산
    remaining_minutes = max(0, target_minutes - current_minutes)
    
    if remaining_minutes == 0:
        return {free_key: 0, paid_1hour_key: 0}  # 추가 쿠폰 불필요
    
    # 남은 시간을 쿠폰으로 채우는 로직...
```

---

## 실행 결과 예시

### C 매장 평일 케이스
```
📍 6단계: 쿠폰 적용 (할인 로직 기반)
   🔍 현재 적용된 쿠폰 파싱 시작...
   📊 현재 적용된 쿠폰 없음 (새로 적용 가능)
   📅 평일 모드: 3시간 할인 목표
   📊 현재 적용된 할인: 0분 (무료 2시간: 0개, 유료 1시간: 0개)
   📊 추가 필요 할인: 180분
   📊 추가 적용할 쿠폰:
     - FREE_2HOUR: 1개
     - PAID_1HOUR: 1개
```

### 이미 일부 쿠폰 적용된 경우 (가상 예시)
```
📍 6단계: 쿠폰 적용 (할인 로직 기반)
   🔍 현재 적용된 쿠폰 파싱 시작...
   📊 현재 적용된 쿠폰 내역:
     - 매장 내역: {'PAID_1HOUR': 1}
     - 전체 내역: {'PAID_1HOUR': 1}
   📅 평일 모드: 3시간 할인 목표
   📊 현재 적용된 할인: 60분 (무료 2시간: 0개, 유료 1시간: 1개)
   📊 추가 필요 할인: 120분
   📊 추가 적용할 쿠폰:
     - FREE_2HOUR: 1개  # 2시간 무료로 남은 120분 커버
     - PAID_1HOUR: 0개  # 추가 유료 쿠폰 불필요
```

---

## 장점

### 1. **정확한 계산**
- 중복 적용 방지
- 과도한 쿠폰 사용 방지
- 목표 시간 정확히 달성

### 2. **매장 간 일관성**
- 모든 매장 동일한 로직 적용
- 새로운 매장 추가 시 설정만 추가하면 됨

### 3. **유지보수성**
- 공통 유틸리티로 중복 코드 제거
- 버그 수정 시 한 곳만 수정하면 됨

### 4. **확장성**
- 새로운 쿠폰 타입 추가 용이
- 새로운 할인 정책 적용 용이

---

## 적용 가이드

### 기존 매장에 적용하기

1. **매장별 설정 추가**
   ```python
   # StoreConfig.get_coupon_config()에 새 매장 설정 추가
   "D": {
       "coupon_key_mapping": {...},
       "coupon_durations": {...}, 
       "discount_selectors": [...]
   }
   ```

2. **파싱 함수 교체**
   ```python
   # 기존
   def _parse_current_coupons(self):
       # 매장별 개별 구현...
   
   # 개선됨
   async def _parse_current_applied_coupons(self):
       store_config = StoreConfig.get_coupon_config(self.store_id)
       return await CommonCouponCalculator.parse_applied_coupons(...)
   ```

3. **계산 로직 업데이트**
   ```python
   # 현재 쿠폰을 매개변수로 받도록 수정
   def _calculate_required_coupons(self, my_history, total_history):
       # 차감 계산 로직 구현...
   ```

---

## 테스트 검증

### 확인 사항
- [ ] 현재 적용된 쿠폰 파싱 정상 동작
- [ ] 차감 계산 정확성
- [ ] 목표 시간 달성 여부
- [ ] 과도한 쿠폰 적용 방지
- [ ] 매장별 설정 정상 로드

### 테스트 케이스
1. **쿠폰 없는 상태에서 시작**
2. **일부 쿠폰 이미 적용된 상태**  
3. **목표 시간 이미 달성된 상태**
4. **무료 쿠폰 사용 제한 케이스**

---

이 문서는 모든 매장에서 현재 적용된 쿠폰을 정확히 파싱하고 차감하여 필요한 쿠폰만 계산하는 통합 로직을 제시합니다. 