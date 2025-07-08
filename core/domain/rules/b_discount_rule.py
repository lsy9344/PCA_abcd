"""
B 매장 할인 규칙 - 실제 테스트 검증된 버전
- PAID_30MIN: 유료 30분할인 (남은잔여량에서 계산)
- FREE_1HOUR: 무료 1시간할인 (무제한 사용 가능)
"""
from typing import Dict
import logging


class BDiscountRule:
    """B 매장 할인 규칙 - 실제 테스트 검증된 버전"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # B 매장 쿠폰 타입 정의 (실제 크롤링 결과와 일치)
        self.coupon_types = {
            'FREE_30MIN': '무료 30분할인',    # 무료 30분 할인
            'FREE_1HOUR': '무료 1시간할인',   # 무제한 사용 가능
            'PAID_30MIN': '유료 30분할인',    # 남은잔여량 ÷ 300
            'PAID_1HOUR': '유료 1시간할인',   # 유료 1시간 할인
            'PAID_24HOUR': '유료 24시간할인'  # 필요시 추가
        }
    
    def decide_coupon_to_apply(
        self, 
        my_history: Dict[str, int], 
        total_history: Dict[str, int], 
        discount_info: Dict[str, int]
    ) -> Dict[str, int]:
        """
        B 매장 쿠폰 적용 개수 결정 - A 매장과 동일한 규칙 적용
        
        Args:
            my_history: 우리 매장 할인 내역 (등록자가 '215'인 경우)
            total_history: 전체 할인 내역 (모든 등록자)
            discount_info: 보유 쿠폰 정보 (PAID_30MIN 개수 등)
        
        Returns:
            적용할 쿠폰 타입별 개수 {'PAID_30MIN': 2, 'FREE_1HOUR': 1} 등
        """
        try:
            from datetime import datetime
            import calendar
            
            coupons_to_apply = {'FREE_1HOUR': 0, 'PAID_30MIN': 0}
            
            # 평일/주말 구분
            today = datetime.now()
            is_weekday = today.weekday() < 5  # 월~금 = 0~4
            
            # 목표 할인 시간 (A 매장과 동일한 규칙)
            if is_weekday:
                target_hours = 3  # 평일 3시간
                self.logger.info("📅 평일 - 목표 할인: 3시간")
            else:
                target_hours = 2  # 주말 2시간
                self.logger.info("📅 주말 - 목표 할인: 2시간")
            
            # 현재 적용된 할인 계산 (모든 쿠폰 타입 포함)
            current_free_30min = my_history.get('FREE_30MIN', 0)
            current_free_1hour = my_history.get('FREE_1HOUR', 0)
            current_paid_30min = my_history.get('PAID_30MIN', 0)
            current_paid_1hour = my_history.get('PAID_1HOUR', 0)
            
            current_hours = (current_free_30min * 0.5) + current_free_1hour + (current_paid_30min * 0.5) + current_paid_1hour
            
            self.logger.info(f"📊 현재 적용된 할인: {current_hours}시간")
            self.logger.info(f"   - 무료 30분: {current_free_30min}개")
            self.logger.info(f"   - 무료 1시간: {current_free_1hour}개") 
            self.logger.info(f"   - 유료 30분: {current_paid_30min}개")
            self.logger.info(f"   - 유료 1시간: {current_paid_1hour}개")
            
            if current_hours >= target_hours:
                self.logger.info("✅ 이미 목표 할인 시간 달성")
                return coupons_to_apply
            
            remaining_hours = target_hours - current_hours
            self.logger.info(f"📊 추가 필요 할인: {remaining_hours}시간")
            
            # A 매장과 동일한 규칙 적용 - 무료 쿠폰 원칙 적용
            # 1. 무료 1시간할인 적용 (my_history 또는 total_history 중 어느 하나라도 사용되었다면 적용하지 않음)
            total_free_used = total_history.get('FREE_1HOUR', 0)
            my_free_used = my_history.get('FREE_1HOUR', 0)
            
            if my_free_used > 0:
                self.logger.info(f"ℹ️ 무료 1시간할인 이미 사용됨 - 현재 매장: {my_free_used}개")
            elif total_free_used > 0:
                self.logger.info(f"ℹ️ 무료 1시간할인 이미 사용됨 - 전체 매장: {total_free_used}개")
            else:
                # 무료 쿠폰이 한 번도 사용되지 않았을 때만 적용
                free_apply = 1
                coupons_to_apply['FREE_1HOUR'] = free_apply
                remaining_hours -= 1
                self.logger.info(f"🎫 무료 1시간할인 {free_apply}개 적용 예정 (무료 쿠폰 미사용 확인됨)")
            
            # 2. 남은 시간을 유료 30분할인으로 채우기
            if remaining_hours > 0:
                # 30분 단위로 계산 (1시간 = 2개, 0.5시간 = 1개)
                paid_30min_needed = int(remaining_hours * 2)  # 1시간 = 2개의 30분
                paid_30min_available = discount_info.get('PAID_30MIN', 0)
                
                paid_apply = min(paid_30min_needed, paid_30min_available)
                if paid_apply > 0:
                    coupons_to_apply['PAID_30MIN'] = paid_apply
                    self.logger.info(f"🎫 유료 30분할인 {paid_apply}개 적용 예정 (보유: {paid_30min_available}개)")
                else:
                    self.logger.warning(f"⚠️ 유료 30분할인 부족: 필요 {paid_30min_needed}개, 보유 {paid_30min_available}개")
            
            self.logger.info(f"📋 B 매장 최종 적용 계획: {coupons_to_apply}")
            return coupons_to_apply
            
        except Exception as e:
            self.logger.error(f"❌ B 매장 쿠폰 적용 계산 중 오류: {str(e)}")
            return {'FREE_1HOUR': 0, 'PAID_30MIN': 0}
    
    def _calculate_current_discount(self, my_history: Dict[str, int]) -> int:
        """현재 적용된 할인 시간 계산 (분 단위)"""
        total_minutes = 0
        
        # 각 쿠폰 타입별 할인 시간 계산
        for coupon_type, count in my_history.items():
            if coupon_type == 'FREE_30MIN':
                total_minutes += count * 30
            elif coupon_type == 'FREE_1HOUR':
                total_minutes += count * 60
            elif coupon_type == 'PAID_30MIN':
                total_minutes += count * 30
            elif coupon_type == 'PAID_1HOUR':
                total_minutes += count * 60
            elif coupon_type == 'PAID_24HOUR':
                total_minutes += count * 24 * 60
            else:
                self.logger.warning(f"⚠️ 알 수 없는 쿠폰 타입: {coupon_type}")
        
        return total_minutes 