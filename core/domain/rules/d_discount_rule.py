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
    DiscountCalculator, DiscountPolicy, CouponConfig
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
        
        # 쿠폰 타입 매핑 (설정 기반 - 룰 파일 원칙 준수)
        # 10_discount_logic.mdc: "쿠폰명/코드명을 모두 '공통 설정'에서 불러와 사용"
        self.coupon_types = {}
        for config_item in self.coupon_configs:
            if config_item.coupon_type == 'FREE':
                self.coupon_types['FREE_1HOUR'] = config_item.coupon_name  # "1시간 무료"
            elif config_item.coupon_type == 'PAID':
                self.coupon_types['PAID_30MIN'] = config_item.coupon_name  # "30분 유료"
        
        self.logger.info(f"[D 매장] YAML 기반 쿠폰 매핑: {self.coupon_types}")
    
    def decide_coupon_to_apply(
        self, 
        my_history: Dict[str, int], 
        total_history: Dict[str, int], 
        discount_info: Dict[str, int]
    ) -> Dict[str, int]:
        """
        D 매장 쿠폰 적용 개수 결정 - 룰 파일 기반 동적 계산 알고리즘
        
        핵심 원칙 (11_calculation_principles.mdc 준수):
        1. 전체 시간 고려: 부족분 = 목표시간 - (기존무료 + 기존유료 + 추가무료)
        2. 설정 기반 계산: duration_minutes 활용한 동적 계산
        3. D 매장 특징: 30분 단위 유료 쿠폰, WEEKEND fallback to PAID
        
        Args:
            my_history: 우리 매장 할인 내역 (쿠폰명 기준)
            total_history: 전체 할인 내역 (쿠폰명 기준)
            discount_info: 보유 쿠폰 정보 (쿠폰명 기준)
        
        Returns:
            적용할 쿠폰 타입별 개수 {'FREE_1HOUR': n, 'PAID_30MIN': m}
        """
        try:
            from datetime import datetime
            import math
            
            # 평일/주말 구분
            today = datetime.now()
            is_weekday = today.weekday() < 5
            target_minutes = 180 if is_weekday else 120  # 3시간/2시간
            
            self.logger.info(f"[D 매장] {'평일' if is_weekday else '주말'} 계산 시작 - 목표: {target_minutes}분")
            self.logger.info(f"[D 매장] 입력 - 내 이력: {my_history}")
            self.logger.info(f"[D 매장] 입력 - 전체 이력: {total_history}")
            self.logger.info(f"[D 매장] 입력 - 보유 쿠폰: {discount_info}")
            
            # 1단계: 현재 적용된 시간 계산 (룰 파일 핵심 원칙)
            current_applied = 0
            for config in self.coupon_configs:
                # 쿠폰명으로 이력 조회
                if config.coupon_type == 'FREE':
                    # 무료 쿠폰: 전체 이력과 내 이력 중 최대값
                    total_used = total_history.get(config.coupon_name, 0)
                    my_used = my_history.get(config.coupon_name, 0)
                    used_count = max(total_used, my_used)
                else:
                    # 유료 쿠폰: 내 이력만 사용
                    used_count = my_history.get(config.coupon_name, 0)
                
                current_applied += used_count * config.duration_minutes
                if used_count > 0:
                    self.logger.info(f"[D 매장] 기존 적용: {config.coupon_name} {used_count}개 = {used_count * config.duration_minutes}분")
            
            self.logger.info(f"[D 매장] 현재 적용된 총 시간: {current_applied}분")
            
            # 2단계: 남은 시간 계산
            remaining_minutes = max(0, target_minutes - current_applied)
            self.logger.info(f"[D 매장] 남은 시간: {remaining_minutes}분")
            
            if remaining_minutes == 0:
                self.logger.info("[D 매장] 이미 목표 달성 - 추가 쿠폰 불필요")
                return {'FREE_1HOUR': 0, 'PAID_30MIN': 0}
            
            # 3단계: 추가 무료 쿠폰 적용 (조건 확인)
            result = {'FREE_1HOUR': 0, 'PAID_30MIN': 0}
            
            # 무료 쿠폰 설정 찾기
            free_config = next((c for c in self.coupon_configs if c.coupon_type == 'FREE'), None)
            if free_config:
                # 무료 쿠폰 사용 가능 조건 확인
                total_free_used = total_history.get(free_config.coupon_name, 0)
                my_free_used = my_history.get(free_config.coupon_name, 0)
                # discount_info가 dict 구조일 경우 처리
                coupon_data = discount_info.get(free_config.coupon_name, 0)
                if isinstance(coupon_data, dict):
                    available_free = max(coupon_data.get('car', 0), coupon_data.get('total', 0))
                else:
                    available_free = coupon_data
                
                # 룰 파일 원칙: 이미 무료 쿠폰을 사용했다면 추가 적용 불가
                can_apply_free = (total_free_used == 0 and my_free_used == 0 and available_free > 0 
                                and remaining_minutes >= free_config.duration_minutes)
                
                self.logger.info(f"[D 매장] 무료 쿠폰 조건 체크: 전체사용={total_free_used}, 내사용={my_free_used}, 보유={available_free}, 남은시간={remaining_minutes}분")
                
                if can_apply_free:
                    result['FREE_1HOUR'] = 1
                    remaining_minutes -= free_config.duration_minutes
                    self.logger.info(f"[D 매장] 무료 쿠폰 적용: {free_config.coupon_name} 1개 ({free_config.duration_minutes}분)")
                else:
                    self.logger.info(f"[D 매장] 무료 쿠폰 적용 불가 - 이미 사용됨 또는 조건 미충족")
            
            # 4단계: 유료 쿠폰으로 부족분 채우기
            if remaining_minutes > 0:
                # D 매장 특징: 주말에도 PAID 타입 사용 (WEEKEND 없음)
                paid_configs = [c for c in self.coupon_configs if c.coupon_type == 'PAID']
                
                if paid_configs:
                    # 가장 우선순위 높은 유료 쿠폰 선택
                    paid_config = sorted(paid_configs, key=lambda x: x.priority)[0]
                    # discount_info가 dict 구조일 경우 처리
                    coupon_data = discount_info.get(paid_config.coupon_name, 0)
                    if isinstance(coupon_data, dict):
                        available_paid = max(coupon_data.get('car', 0), coupon_data.get('total', 0))
                    else:
                        available_paid = coupon_data
                    
                    self.logger.info(f"[D 매장] 유료 쿠폰 정보: {paid_config.coupon_name}, 보유={available_paid}개, duration={paid_config.duration_minutes}분")
                    
                    if available_paid > 0:
                        # D 매장 특징: 30분 단위 쿠폰 - math.ceil로 올림 처리
                        needed_paid = math.ceil(remaining_minutes / paid_config.duration_minutes)
                        actual_paid = min(needed_paid, available_paid)
                        
                        self.logger.info(f"[D 매장] 유료 쿠폰 계산: {remaining_minutes}분 ÷ {paid_config.duration_minutes}분 = {needed_paid}개 필요, 실제 적용={actual_paid}개")
                        
                        if actual_paid > 0:
                            result['PAID_30MIN'] = actual_paid
                            applied_minutes = actual_paid * paid_config.duration_minutes
                            remaining_minutes = max(0, remaining_minutes - applied_minutes)
                            
                            self.logger.info(f"[D 매장] 유료 쿠폰 적용: {paid_config.coupon_name} {actual_paid}개 ({applied_minutes}분)")
                    else:
                        self.logger.info(f"[D 매장] 유료 쿠폰 보유량 부족: {available_paid}개")
            
            # 5단계: 최종 검증 및 결과 로깅
            total_apply_minutes = 0
            if result['FREE_1HOUR'] > 0 and free_config:
                total_apply_minutes += result['FREE_1HOUR'] * free_config.duration_minutes
            if result['PAID_30MIN'] > 0 and paid_configs:
                paid_config = sorted(paid_configs, key=lambda x: x.priority)[0]
                total_apply_minutes += result['PAID_30MIN'] * paid_config.duration_minutes
            
            final_total = current_applied + total_apply_minutes
            
            self.logger.info(f"[D 매장] 최종 적용 계획: {result}")
            self.logger.info(f"[D 매장] 추가 적용 시간: {total_apply_minutes}분")
            self.logger.info(f"[D 매장] 총 적용 시간: {final_total}분 (목표: {target_minutes}분)")
            
            if final_total >= target_minutes:
                self.logger.info("[D 매장] ✅ 목표 시간 달성")
            else:
                self.logger.warning(f"[D 매장] ⚠️ 목표 미달성 ({target_minutes - final_total}분 부족)")
            
            if not is_weekday:
                self.logger.info("[D 매장] 주말 특징: WEEKEND 쿠폰 없음 → PAID 타입으로 대체")
            
            return result
            
        except Exception as e:
            self.logger.error(f"[실패] D 매장 쿠폰 계산 오류: {str(e)}")
            import traceback
            self.logger.error(f"[실패] 스택 트레이스:\n{traceback.format_exc()}")
            return {'FREE_1HOUR': 0, 'PAID_30MIN': 0}
    
    def _convert_history_keys(self, history_by_name: Dict[str, int]) -> Dict[str, int]:
        """이력 키 변환: coupon_name → coupon_key (더 이상 사용하지 않음 - 직접 coupon_name 사용)"""
        # 룰 파일 원칙에 따라 설정 기반 동적 접근법으로 변경
        # 이제 coupon_name을 직접 사용하므로 변환 불필요
        return history_by_name
    
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