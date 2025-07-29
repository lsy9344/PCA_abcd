"""
A 매장 할인 규칙
- FREE_1HOUR: 무료 1시간할인 (무제한 사용 가능)
- PAID_1HOUR: 유료 1시간할인 (평일 기준)
- WEEKEND_1HOUR: 주말 1시간할인 (주말 기준)
"""
from typing import Dict
import logging
from core.domain.models.discount_policy import DiscountCalculator, DiscountPolicy, CouponRule


class ADiscountRule:
    """A 매장 할인 규칙"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # A 매장용 DiscountCalculator 인스턴스 생성
        policy = DiscountPolicy(store_id="A")
        coupon_rules = [
            CouponRule("FREE_1HOUR", "30분할인권(무료)", "free", 60, 0),
            CouponRule("PAID_1HOUR", "1시간할인권(유료)", "paid", 60, 1),
            CouponRule("WEEKEND_1HOUR", "1시간주말할인권(유료)", "weekend", 60, 2)
        ]
        self.calculator = DiscountCalculator(policy, coupon_rules)
        
        # A 매장 쿠폰 타입 정의
        self.coupon_types = {
            'FREE_1HOUR': '30분할인권(무료)',
            'PAID_1HOUR': '1시간할인권(유료)', 
            'WEEKEND_1HOUR': '1시간주말할인권(유료)'
        }
    
    def decide_coupon_to_apply(
        self, 
        my_history: Dict[str, int], 
        total_history: Dict[str, int], 
        discount_info: Dict[str, int]
    ) -> Dict[str, int]:
        """
        A 매장 쿠폰 적용 개수 결정
        
        Args:
            my_history: 우리 매장 할인 내역
            total_history: 전체 할인 내역
            discount_info: 보유 쿠폰 정보
        
        Returns:
            적용할 쿠폰 타입별 개수
        """
        try:
            from datetime import datetime
            
            # 평일/주말 구분
            today = datetime.now()
            is_weekday = today.weekday() < 5
            
            # DiscountCalculator로 계산
            applications = self.calculator.calculate_required_coupons(
                my_history=my_history,
                total_history=total_history,
                available_coupons=discount_info,
                is_weekday=is_weekday
            )
            
            # 레거시 형식으로 변환
            result = {'FREE_1HOUR': 0, 'PAID_1HOUR': 0, 'WEEKEND_1HOUR': 0}
            for app in applications:
                if '무료' in app.coupon_name:
                    result['FREE_1HOUR'] = app.count
                elif '주말' in app.coupon_name:
                    result['WEEKEND_1HOUR'] = app.count
                elif '유료' in app.coupon_name:
                    result['PAID_1HOUR'] = app.count
            
            self.logger.info(f"[최종] A 매장 쿠폰 적용 계획: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"[실패] A 매장 쿠폰 적용 계산 중 오류: {str(e)}")
            return {'FREE_1HOUR': 0, 'PAID_1HOUR': 0, 'WEEKEND_1HOUR': 0}
    
    def _calculate_current_discount(self, my_history: Dict[str, int]) -> int:
        """현재 적용된 할인 시간 계산 (분 단위)"""
        total_minutes = 0
        
        # 각 쿠폰 타입별 할인 시간 계산
        for coupon_type, count in my_history.items():
            if coupon_type in ['FREE_1HOUR', 'PAID_1HOUR', 'WEEKEND_1HOUR']:
                total_minutes += count * 60
            else:
                self.logger.warning(f"[경고] 알 수 없는 쿠폰 타입: {coupon_type}")
        
        return total_minutes