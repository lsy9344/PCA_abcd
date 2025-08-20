"""
할인 정책 도메인 모델 - 4_discount_logic.mdc 기반 동적 계산
"""
from dataclasses import dataclass
from typing import Dict, List
import math
from .coupon import CouponApplication, CouponType


@dataclass
class DiscountPolicy:
    """할인 정책 - 시간 독립적 설계"""
    store_id: str
    weekday_target_minutes: int = 180  # 3시간 = 180분
    weekend_target_minutes: int = 120  # 2시간 = 120분
    
    def get_target_minutes(self, is_weekday: bool) -> int:
        """목표 할인 시간 조회 (분 단위)"""
        return self.weekday_target_minutes if is_weekday else self.weekend_target_minutes


@dataclass 
class CouponConfig:
    """쿠폰 설정 - duration_minutes 기반"""
    coupon_key: str
    coupon_name: str
    coupon_type: str  # "FREE", "PAID", "WEEKEND"
    duration_minutes: int
    priority: int = 0  # 우선순위 (낮을수록 우선)
    
    def get_duration_hours(self) -> float:
        """시간 단위로 변환"""
        return self.duration_minutes / 60.0


@dataclass
class CouponRule:
    """
    DEPRECATED: 레거시 호환용 쿠폰 규칙 - CouponConfig 사용 권장
    향후 버전에서 제거 예정
    """
    coupon_key: str
    coupon_name: str
    coupon_type: CouponType
    duration_minutes: int
    priority: int = 0
    
    def get_duration_hours(self) -> float:
        return self.duration_minutes / 60.0
    
    def __post_init__(self):
        import warnings
        warnings.warn(
            "CouponRule은 deprecated되었습니다. CouponConfig를 사용하세요.",
            DeprecationWarning,
            stacklevel=2
        )


def calculate_dynamic_coupons(
    target_minutes: int,           # 목표 시간 (분 단위)
    coupon_configs: List[CouponConfig],  # 매장별 쿠폰 설정
    my_history: Dict[str, int],    # 매장별 사용 이력
    total_history: Dict[str, int], # 전체 무료 쿠폰 이력
    is_weekday: bool
) -> Dict[str, int]:
    """
    설정 기반 동적 쿠폰 계산 알고리즘 (4_discount_logic.mdc 기반)
    - 매장마다 다른 쿠폰 시간에 대응
    - 새로운 쿠폰 타입 추가 시 코드 변경 불필요
    """
    applications = {}
    remaining_minutes = target_minutes
    
    # 현재 적용된 시간 계산 (무료 쿠폰은 전체 이력, 유료 쿠폰은 매장별 이력)
    current_minutes = 0
    for config in coupon_configs:
        if config.coupon_type == 'FREE':
            # 무료 쿠폰: 전체 이력과 매장 이력 중 최대값 사용
            total_used = total_history.get(config.coupon_key, 0)
            my_used = my_history.get(config.coupon_key, 0)
            used_count = max(total_used, my_used)
        else:
            # 유료/주말 쿠폰: 매장별 이력만 사용
            used_count = my_history.get(config.coupon_key, 0)
        current_minutes += used_count * config.duration_minutes
    
    remaining_minutes = max(0, target_minutes - current_minutes)
    
    if remaining_minutes == 0:
        return applications  # 이미 목표 달성
    
    # 1단계: 무료 쿠폰 우선 적용
    free_coupons = [c for c in coupon_configs if c.coupon_type == 'FREE']
    for config in sorted(free_coupons, key=lambda x: x.priority):
        # 전체 이력에서 무료 쿠폰 사용 여부 확인
        total_free_used = total_history.get(config.coupon_key, 0)
        my_free_used = my_history.get(config.coupon_key, 0)
        
        # 무료 쿠폰은 전체적으로 또는 이 매장에서 이미 사용했다면 더 이상 적용 불가
        if total_free_used > 0 or my_free_used > 0:
            continue  # 이미 사용됨 (전체 또는 이 매장에서)
        
        # 무료 쿠폰 적용 가능한 개수 계산
        free_needed_count = min(
            math.ceil(remaining_minutes / config.duration_minutes),
            1  # 무료 쿠폰은 보통 1개 제한
        )
        
        if free_needed_count > 0:
            applications[config.coupon_key] = free_needed_count
            remaining_minutes -= free_needed_count * config.duration_minutes
            remaining_minutes = max(0, remaining_minutes)
    
    # 2단계: 유료/주말 쿠폰으로 남은 시간 채우기
    if remaining_minutes > 0:
        # 평일/주말에 따른 쿠폰 타입 선택
        if is_weekday:
            target_types = ['PAID']
        else:
            # 주말: WEEKEND 우선, 없으면 PAID 사용
            weekend_coupons = [c for c in coupon_configs if c.coupon_type == 'WEEKEND']
            target_types = ['WEEKEND'] if weekend_coupons else ['PAID']
        
        for coupon_type in target_types:
            type_coupons = [c for c in coupon_configs if c.coupon_type == coupon_type]
            
            for config in sorted(type_coupons, key=lambda x: x.priority):
                if remaining_minutes <= 0:
                    break
                
                # 필요한 쿠폰 개수 계산 (올림)
                needed_count = math.ceil(remaining_minutes / config.duration_minutes)
                
                if needed_count > 0:
                    applications[config.coupon_key] = needed_count
                    remaining_minutes -= needed_count * config.duration_minutes
                    remaining_minutes = max(0, remaining_minutes)
    
    return applications


def validate_coupon_application(applications: Dict[str, int], 
                              coupon_configs: List[CouponConfig],
                              target_minutes: int) -> bool:
    """계산 결과 검증"""
    total_applied_minutes = 0
    
    for coupon_key, count in applications.items():
        config = next((c for c in coupon_configs if c.coupon_key == coupon_key), None)
        if config:
            total_applied_minutes += count * config.duration_minutes
    
    return total_applied_minutes >= target_minutes


class DiscountCalculator:
    """할인 계산기 - 동적 계산 알고리즘 사용"""
    
    def __init__(self, policy: DiscountPolicy, coupon_configs: List[CouponConfig]):
        self.policy = policy
        self.coupon_configs = sorted(coupon_configs, key=lambda x: x.priority)
    
    def calculate_required_coupons(self, 
                                 my_history: Dict[str, int],
                                 total_history: Dict[str, int],
                                 available_coupons: Dict[str, int],
                                 is_weekday: bool) -> List[CouponApplication]:
        """
        동적 계산 알고리즘 기반 쿠폰 계산 - 추가로 필요한 쿠폰만 반환
        """
        target_minutes = self.policy.get_target_minutes(is_weekday)
        
        # 현재 적용된 시간 계산
        current_minutes = 0
        for config in self.coupon_configs:
            if config.coupon_type == 'FREE':
                # 무료 쿠폰: 전체 이력과 매장 이력 중 최대값 사용
                total_used = total_history.get(config.coupon_key, 0)
                my_used = my_history.get(config.coupon_key, 0)
                used_count = max(total_used, my_used)
            else:
                # 유료/주말 쿠폰: 매장별 이력만 사용
                used_count = my_history.get(config.coupon_key, 0)
            current_minutes += used_count * config.duration_minutes
        
        print(f"   📊 현재 적용된 할인: {current_minutes}분")
        print(f"   🎯 목표 할인: {target_minutes}분")
        
        # 이미 목표 달성한 경우
        if current_minutes >= target_minutes:
            print(f"   ✅ 이미 목표 달성됨 (현재: {current_minutes}분 >= 목표: {target_minutes}분)")
            return []
        
        # 사용되지 않는 변수들 제거됨 (empty_my_history, empty_total_history)
        
        # 남은 시간 계산
        remaining_minutes = target_minutes - current_minutes
        print(f"   📊 추가 필요한 할인: {remaining_minutes}분")
        
        # 단순히 남은 시간에 대해 쿠폰 계산 (동적 알고리즘 우회)
        applications_dict = {}
        
        if remaining_minutes > 0:
            # 무료 쿠폰이 이미 사용되었는지 확인
            free_already_used = False
            for config in self.coupon_configs:
                if config.coupon_type == 'FREE':
                    total_used = total_history.get(config.coupon_key, 0)
                    my_used = my_history.get(config.coupon_key, 0)
                    if total_used > 0 or my_used > 0:
                        free_already_used = True
                        break
            
            # 무료 쿠폰 적용 (아직 사용 안했고, 남은 시간이 충분한 경우)
            if not free_already_used:
                for config in self.coupon_configs:
                    if config.coupon_type == 'FREE' and remaining_minutes >= config.duration_minutes:
                        applications_dict[config.coupon_key] = 1
                        remaining_minutes -= config.duration_minutes
                        break
            
            # 유료/주말 쿠폰으로 남은 시간 채우기
            if remaining_minutes > 0:
                if is_weekday:
                    target_types = ['PAID']
                else:
                    # 주말: WEEKEND 우선, 없으면 PAID 사용
                    weekend_coupons = [c for c in self.coupon_configs if c.coupon_type == 'WEEKEND']
                    target_types = ['WEEKEND'] if weekend_coupons else ['PAID']
                
                for coupon_type in target_types:
                    type_coupons = [c for c in self.coupon_configs if c.coupon_type == coupon_type]
                    
                    for config in sorted(type_coupons, key=lambda x: x.priority):
                        if remaining_minutes <= 0:
                            break
                        
                        # 필요한 쿠폰 개수 계산 (올림)
                        import math
                        needed_count = math.ceil(remaining_minutes / config.duration_minutes)
                        
                        if needed_count > 0:
                            applications_dict[config.coupon_key] = needed_count
                            remaining_minutes -= needed_count * config.duration_minutes
                            remaining_minutes = max(0, remaining_minutes)
                            break
        
        print(f"   📊 추가 필요한 쿠폰: {applications_dict}")
        
        # CouponApplication 객체로 변환
        applications = []
        for coupon_key, count in applications_dict.items():
            config = next((c for c in self.coupon_configs if c.coupon_key == coupon_key), None)
            if config and count > 0:
                # available_coupons 체크 추가
                available = available_coupons.get(config.coupon_name, 0)
                actual_count = min(count, available)
                
                if actual_count > 0:
                    # CouponType 변환
                    coupon_type_map = {
                        'FREE': CouponType.FREE,
                        'PAID': CouponType.PAID,
                        'WEEKEND': CouponType.WEEKEND
                    }
                    
                    applications.append(CouponApplication(
                        coupon_name=config.coupon_name,
                        coupon_type=coupon_type_map.get(config.coupon_type, CouponType.PAID),
                        count=actual_count
                    ))
        
        return applications 