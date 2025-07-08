"""
B 매장 전용 할인 계산기
"""
from typing import Dict, List
from .discount_policy import DiscountCalculator, DiscountPolicy, CouponRule
from .coupon import CouponApplication, CouponType


class BDiscountCalculator(DiscountCalculator):
    """B 매장 전용 할인 계산기 - 기본 규칙 적용"""
    
    def __init__(self, policy: DiscountPolicy, coupon_rules: List[CouponRule]):
        super().__init__(policy, coupon_rules)
    
    def calculate_required_coupons(self, 
                                 my_history: Dict[str, int],
                                 total_history: Dict[str, int],
                                 available_coupons: Dict[str, int],
                                 is_weekday: bool) -> List[CouponApplication]:
        """
        B 매장 쿠폰 계산 - 기본 규칙 적용
        - @/rules 지침에 따라 평일 3시간 적용
        - 2배 보정 로직 제거
        """
        period_type = "평일" if is_weekday else "주말"
        
        print(f"\n{'='*60}")
        print(f"[BDiscountCalculator] B 매장 쿠폰 계산 - {period_type}")
        print(f"{'='*60}")
        print(f"[입력데이터] 매장 쿠폰 사용이력: {my_history}")
        print(f"[입력데이터] 전체 무료쿠폰 이력: {total_history}")
        print(f"[입력데이터] 보유 쿠폰 현황: {available_coupons}")
        
        # 부모 클래스의 기본 계산 수행 (2배 보정 없이)
        applications = super().calculate_required_coupons(
            my_history, total_history, available_coupons, is_weekday
        )
        
        for app in applications:
            coupon_rule = next((rule for rule in self.coupon_rules 
                              if rule.coupon_name == app.coupon_name), None)
            duration = coupon_rule.duration_minutes if coupon_rule else 0
            total_minutes = app.count * duration
            
            print(f">>>>> B매장 최종: {app.coupon_name} {app.count}개 ({total_minutes}분)")
        
        print(f"{'='*60}\n")
        
        return applications 