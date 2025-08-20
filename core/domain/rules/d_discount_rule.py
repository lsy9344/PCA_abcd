"""
D 매장 할인 규칙 - 문서 규칙 기반 동적 계산
- 30분 단위 유료 쿠폰 특화 (B매장과 동일 구조)
- 주말 전용 쿠폰 없음 (PAID fallback)
- YAML 설정 기반 쿠폰 관리
- 쿠폰 적용 후 팝업 미출현 특성 반영
"""
from typing import Dict
import logging
import yaml
from pathlib import Path
from core.domain.models.discount_policy import (
    DiscountCalculator, DiscountPolicy, CouponConfig, calculate_dynamic_coupons
)


class DDiscountRule:
    """D 매장 할인 규칙 - 동적 계산 알고리즘 기반"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # YAML 설정 파일 로드
        config_path = Path(__file__).parent.parent.parent.parent / "infrastructure/config/store_configs/d_store_config.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # DiscountPolicy 생성
        policy_config = config.get('discount_policy', {})
        self.policy = DiscountPolicy(
            store_id="D",
            weekday_target_minutes=policy_config.get('weekday', {}).get('target_hours', 3) * 60,
            weekend_target_minutes=policy_config.get('weekend', {}).get('target_hours', 2) * 60
        )
        
        # CouponConfig 리스트 생성
        self.coupon_configs = []
        coupons_config = config.get('coupons', {})
        for coupon_key, coupon_info in coupons_config.items():
            self.coupon_configs.append(CouponConfig(
                coupon_key=coupon_key,
                coupon_name=coupon_info['name'],
                coupon_type=coupon_info['type'],
                duration_minutes=coupon_info['duration_minutes'],
                priority=coupon_info['priority']
            ))
        
        # DiscountCalculator 생성
        self.calculator = DiscountCalculator(self.policy, self.coupon_configs)
        
        # 쿠폰 타입 매핑 (설정 기반)
        self.coupon_types = {}
        for config_item in self.coupon_configs:
            if config_item.coupon_type == 'FREE':
                self.coupon_types['FREE_1HOUR'] = config_item.coupon_name
            elif config_item.coupon_type == 'PAID':
                self.coupon_types['PAID_30MIN'] = config_item.coupon_name
    
    def decide_coupon_to_apply(
        self, 
        my_history: Dict[str, int], 
        total_history: Dict[str, int], 
        discount_info: Dict[str, int]
    ) -> Dict[str, int]:
        """
        D 매장 쿠폰 적용 개수 결정 - 동적 계산 알고리즘 사용
        D 매장 특징: 30분 단위 유료 쿠폰, 주말 전용 쿠폰 없음 (PAID fallback), 팝업 미출현
        
        Args:
            my_history: 우리 매장 할인 내역
            total_history: 전체 할인 내역  
            discount_info: 보유 쿠폰 정보
        
        Returns:
            적용할 쿠폰 타입별 개수 (레거시 형식)
        """
        try:
            from datetime import datetime
            
            # 평일/주말 구분
            today = datetime.now()
            is_weekday = today.weekday() < 5
            
            self.logger.info(f"[D 매장] {'평일' if is_weekday else '주말'} 쿠폰 계산 시작")
            
            # 목표 시간 (분 단위)
            target_minutes = self.policy.get_target_minutes(is_weekday)
            
            # 이력 키 변환: coupon_name → coupon_key (할인 계산기 호환)
            my_history_by_key = self._convert_history_keys(my_history)
            total_history_by_key = self._convert_history_keys(total_history)
            
            self.logger.info(f"[D 매장] 변환된 내 이력: {my_history_by_key}")
            self.logger.info(f"[D 매장] 변환된 전체 이력: {total_history_by_key}")
            
            # 동적 계산 알고리즘 호출
            applications_dict = calculate_dynamic_coupons(
                target_minutes=target_minutes,
                coupon_configs=self.coupon_configs,
                my_history=my_history_by_key,
                total_history=total_history_by_key,
                is_weekday=is_weekday
            )
            
            self.logger.info(f"[D 매장] 동적 계산 결과: {applications_dict}")
            
            # 보유 쿠폰 체크 및 실제 적용 가능 개수 조정
            final_applications = {}
            for coupon_key, count in applications_dict.items():
                config = next((c for c in self.coupon_configs if c.coupon_key == coupon_key), None)
                if config:
                    available = discount_info.get(config.coupon_name, 0)
                    actual_count = min(count, available)
                    if actual_count > 0:
                        final_applications[coupon_key] = actual_count
                    
                    self.logger.info(f"[D 매장] {config.coupon_name}: 계산값 {count}개, 보유 {available}개 → 적용 {actual_count}개")
            
            # 표준 형식으로 변환 (인터페이스 호환)
            result = {'FREE_1HOUR': 0, 'PAID_30MIN': 0}
            for coupon_key, count in final_applications.items():
                config = next((c for c in self.coupon_configs if c.coupon_key == coupon_key), None)
                if config:
                    if config.coupon_type == 'FREE':
                        result['FREE_1HOUR'] = count
                    elif config.coupon_type == 'PAID':
                        result['PAID_30MIN'] = count
            
            # 계산 결과 검증 및 D매장 특수 조건 확인
            total_apply_minutes = 0
            for coupon_key, count in final_applications.items():
                config = next((c for c in self.coupon_configs if c.coupon_key == coupon_key), None)
                if config:
                    total_apply_minutes += count * config.duration_minutes
            
            # D 매장 특징: 30분 단위 쿠폰으로 인한 추가 로깅
            paid_minutes = result['PAID_30MIN'] * 30
            free_minutes = result['FREE_1HOUR'] * 60
            
            self.logger.info(f"[D 매장] 최종 적용 계획: {result}")
            self.logger.info(f"[D 매장] 무료쿠폰: {result['FREE_1HOUR']}개 ({free_minutes}분)")
            self.logger.info(f"[D 매장] 유료쿠폰: {result['PAID_30MIN']}개 ({paid_minutes}분) - 30분 단위")
            self.logger.info(f"[D 매장] 총 적용 시간: {total_apply_minutes}분 (목표: {target_minutes}분)")
            self.logger.info(f"[D 매장] 목표 달성: {'성공' if total_apply_minutes >= target_minutes else '실패'}")
            
            if not is_weekday:
                self.logger.info("[D 매장] 주말 특징: WEEKEND 쿠폰 없음 → PAID 타입으로 fallback 적용됨")
            
            self.logger.info("[D 매장] 특징: 쿠폰 적용 후 팝업 미출현 - 별도 팝업 처리 불필요")
            
            return result
            
        except Exception as e:
            self.logger.error(f"[실패] D 매장 쿠폰 적용 계산 중 오류: {str(e)}")
            return {'FREE_1HOUR': 0, 'PAID_30MIN': 0}
    
    def _convert_history_keys(self, history_by_name: Dict[str, int]) -> Dict[str, int]:
        """이력 키 변환: coupon_name → coupon_key"""
        history_by_key = {}
        for config in self.coupon_configs:
            if config.coupon_name in history_by_name:
                history_by_key[config.coupon_key] = history_by_name[config.coupon_name]
        return history_by_key
    
    def _calculate_current_discount(self, my_history: Dict[str, int]) -> int:
        """현재 적용된 할인 시간 계산 (분 단위) - 동적 계산"""
        total_minutes = 0
        
        # 쿠폰 설정 기반으로 시간 계산
        for coupon_key, count in my_history.items():
            config = next((c for c in self.coupon_configs if c.coupon_key == coupon_key), None)
            if config:
                total_minutes += count * config.duration_minutes
                self.logger.debug(f"[D매장 시간계산] {config.coupon_name}: {count}개 × {config.duration_minutes}분 = {count * config.duration_minutes}분")
            else:
                # 표준 쿠폰 타입 - D매장 특화 계산 (B매장과 동일)
                if coupon_key == 'FREE_30MIN':
                    total_minutes += count * 30
                elif coupon_key == 'FREE_1HOUR':
                    total_minutes += count * 60
                elif coupon_key == 'PAID_30MIN':
                    total_minutes += count * 30
                elif coupon_key == 'PAID_1HOUR':
                    total_minutes += count * 60
                elif coupon_key == 'PAID_24HOUR':
                    total_minutes += count * 24 * 60
                else:
                    self.logger.warning(f"[경고] 알 수 없는 쿠폰 타입: {coupon_key}")
                    
                if coupon_key in ['FREE_30MIN', 'FREE_1HOUR', 'PAID_30MIN', 'PAID_1HOUR', 'PAID_24HOUR']:
                    self.logger.debug(f"[D매장 시간계산] {coupon_key} (표준): {count}개")
        
        self.logger.info(f"[D매장 시간계산] 총 적용된 할인 시간: {total_minutes}분")
        return total_minutes