"""
C 매장 할인 규칙
- FREE_1HOUR: 무료 1시간할인 (기본 쿠폰)
- PAID_30MIN: 유료 30분할인 (평일 기준)
- PAID_1HOUR: 유료 1시간할인 (평일 기준)
"""
from typing import Dict
import logging
from core.domain.models.discount_policy import DiscountCalculator, DiscountPolicy, CouponRule


class CDiscountRule:
    """C 매장 할인 규칙"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # C 매장용 DiscountCalculator 인스턴스 생성
        policy = DiscountPolicy(store_id="C")
        coupon_rules = [
            CouponRule("FREE_1HOUR", "무료 1시간할인", "free", 60, 0),
            CouponRule("PAID_30MIN", "유료 30분할인", "paid", 30, 1),
            CouponRule("PAID_1HOUR", "유료 1시간할인", "paid", 60, 2)
        ]
        self.calculator = DiscountCalculator(policy, coupon_rules)
        
        # C 매장 쿠폰 타입 정의 (config 파일과 매칭)
        self.coupon_types = {
            'FREE_1HOUR': '무료 1시간할인',
            'PAID_30MIN': '유료 30분할인', 
            'PAID_1HOUR': '유료 1시간할인'
        }
    
    def decide_coupon_to_apply(
        self, 
        my_history: Dict[str, int], 
        total_history: Dict[str, int], 
        discount_info: Dict[str, int]
    ) -> Dict[str, int]:
        """
        C 매장 쿠폰 적용 개수 결정
        
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
            result = {'FREE_1HOUR': 0, 'PAID_30MIN': 0, 'PAID_1HOUR': 0}
            for app in applications:
                if '무료' in app.coupon_name and '1시간' in app.coupon_name:
                    result['FREE_1HOUR'] = app.count
                elif '유료' in app.coupon_name and '30분' in app.coupon_name:
                    result['PAID_30MIN'] = app.count
                elif '유료' in app.coupon_name and '1시간' in app.coupon_name:
                    result['PAID_1HOUR'] = app.count
            
            self.logger.info(f"[최종] C 매장 쿠폰 적용 계획: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"[실패] C 매장 쿠폰 적용 계산 중 오류: {str(e)}")
            return {'FREE_1HOUR': 0, 'PAID_30MIN': 0, 'PAID_1HOUR': 0}
    
    def _calculate_current_discount(self, my_history: Dict[str, int]) -> int:
        """현재 적용된 할인 시간 계산 (분 단위)"""
        total_minutes = 0
        
        # 각 쿠폰 타입별 할인 시간 계산
        for coupon_type, count in my_history.items():
            if coupon_type == 'FREE_1HOUR' or coupon_type == 'PAID_1HOUR':
                total_minutes += count * 60
            elif coupon_type == 'PAID_30MIN':
                total_minutes += count * 30
            else:
                self.logger.warning(f"[경고] 알 수 없는 쿠폰 타입: {coupon_type}")
        
        return total_minutes