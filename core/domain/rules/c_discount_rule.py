"""
C 매장 할인 규칙
- FREE_2HOUR: 무료 2시간할인 (기본 쿠폰)
- PAID_1HOUR: 유료 1시간할인 (평일 기준)
"""
from typing import Dict
import logging
import yaml
import os
from core.domain.models.discount_policy import DiscountCalculator, DiscountPolicy, CouponConfig
from core.domain.models.coupon import CouponType


class CDiscountRule:
    """C 매장 할인 규칙 - 설정 기반 동적 계산"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 설정 파일에서 쿠폰 정보 로드
        self.config = self._load_store_config()
        
        # DiscountPolicy 생성 (설정 기반)
        policy = DiscountPolicy(
            store_id="C",
            weekday_target_minutes=self.config['policy']['weekday_target_minutes'],
            weekend_target_minutes=self.config['policy']['weekend_target_minutes']
        )
        
        # CouponConfig 리스트 생성 (설정 기반)
        coupon_configs = []
        for coupon_key, coupon_data in self.config['coupons'].items():
            coupon_configs.append(CouponConfig(
                coupon_key=coupon_key,
                coupon_name=coupon_data['name'],
                coupon_type=coupon_data['type'],
                duration_minutes=coupon_data['duration_minutes'],
                priority=coupon_data['priority']
            ))
        
        self.calculator = DiscountCalculator(policy, coupon_configs)
        
        # 쿠폰 키-이름 매핑 (설정 기반)
        self.coupon_key_to_name = {
            coupon_key: coupon_data['name'] 
            for coupon_key, coupon_data in self.config['coupons'].items()
        }
        self.coupon_name_to_key = {
            coupon_data['name']: coupon_key 
            for coupon_key, coupon_data in self.config['coupons'].items()
        }
    
    def _load_store_config(self) -> Dict:
        """C 매장 설정 파일 로드"""
        config_path = os.path.join(
            os.path.dirname(__file__), 
            '../../../infrastructure/config/store_configs/c_store_config.yaml'
        )
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"설정 파일 로드 실패: {e}")
            # 기본값 반환
            return {
                'coupons': {
                    'FREE_2HOUR': {
                        'name': '무료 2시간할인',
                        'type': 'FREE',
                        'duration_minutes': 120,
                        'priority': 0
                    },
                    'PAID_1HOUR': {
                        'name': '1시간 유료할인권',
                        'type': 'PAID',
                        'duration_minutes': 60,
                        'priority': 1
                    }
                },
                'policy': {
                    'weekday_target_minutes': 180,
                    'weekend_target_minutes': 120
                }
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
            
            # 설정 기반 동적 결과 딕셔너리 생성
            result = {coupon_key: 0 for coupon_key in self.config['coupons'].keys()}
            
            # 쿠폰 이름을 키로 변환 (설정 기반)
            for app in applications:
                coupon_key = self.coupon_name_to_key.get(app.coupon_name)
                if coupon_key and coupon_key in result:
                    result[coupon_key] = app.count
            
            self.logger.info(f"[최종] C 매장 쿠폰 적용 계획: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"[실패] C 매장 쿠폰 적용 계산 중 오류: {str(e)}")
            # 설정 기반 동적 오류 반환값 생성
            return {coupon_key: 0 for coupon_key in self.config['coupons'].keys()}
    
    def _calculate_current_discount(self, my_history: Dict[str, int]) -> int:
        """현재 적용된 할인 시간 계산 (분 단위) - 설정 기반"""
        total_minutes = 0
        
        # 설정에서 쿠폰별 시간 정보를 가져와서 계산
        for coupon_key, count in my_history.items():
            coupon_data = self.config['coupons'].get(coupon_key)
            if coupon_data:
                total_minutes += count * coupon_data['duration_minutes']
            else:
                self.logger.warning(f"[경고] 설정에 정의되지 않은 쿠폰 타입: {coupon_key}")
        
        return total_minutes