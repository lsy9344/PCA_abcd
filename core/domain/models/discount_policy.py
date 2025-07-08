"""
할인 정책 도메인 모델
"""
from dataclasses import dataclass
from typing import Dict, List
from datetime import datetime
from .coupon import CouponApplication, CouponType


@dataclass
class DiscountPolicy:
    """할인 정책"""
    store_id: str
    weekday_target_hours: int = 3
    weekend_target_hours: int = 2
    weekday_max_coupons: int = 5
    weekend_max_coupons: int = 3
    
    # 쿠폰 타입별 목표 개수 (룰파일 4.2-4.3)
    free_coupon_target_count: int = 1  # 무료 쿠폰 목표 개수
    weekday_paid_target_count: int = 2  # 평일 유료 쿠폰 목표 개수 (2시간)
    weekend_coupon_target_count: int = 1  # 주말 쿠폰 목표 개수 (1시간)
    
    def get_target_hours(self, is_weekday: bool) -> int:
        """목표 할인 시간 조회"""
        return self.weekday_target_hours if is_weekday else self.weekend_target_hours
    
    def get_max_coupons(self, is_weekday: bool) -> int:
        """최대 쿠폰 개수 조회"""
        return self.weekday_max_coupons if is_weekday else self.weekend_max_coupons
    
    def get_coupon_target_count(self, coupon_type: CouponType, is_weekday: bool) -> int:
        """쿠폰 타입별 목표 개수 조회 (룰파일 4.2-4.3)"""
        if coupon_type == CouponType.FREE:
            return self.free_coupon_target_count
        elif coupon_type == CouponType.PAID and is_weekday:
            return self.weekday_paid_target_count
        elif coupon_type == CouponType.WEEKEND and not is_weekday:
            return self.weekend_coupon_target_count
        else:
            return 0


@dataclass
class CouponRule:
    """쿠폰 규칙"""
    coupon_key: str
    coupon_name: str
    coupon_type: CouponType
    duration_minutes: int
    priority: int = 0  # 우선순위 (낮을수록 우선)
    
    def get_duration_hours(self) -> float:
        """시간 단위로 변환"""
        return self.duration_minutes / 60.0


class DiscountCalculator:
    """할인 계산기"""
    
    def __init__(self, policy: DiscountPolicy, coupon_rules: List[CouponRule]):
        self.policy = policy
        self.coupon_rules = sorted(coupon_rules, key=lambda x: x.priority)
    
    def calculate_required_coupons(self, 
                                 my_history: Dict[str, int],
                                 total_history: Dict[str, int],
                                 available_coupons: Dict[str, int],
                                 is_weekday: bool) -> List[CouponApplication]:
        """
        @/rules 지침에 따른 쿠폰 계산
        - 이미 적용된 쿠폰을 고려하여 부족한 만큼만 추가 적용
        - 평일: 총 3시간 = 무료 1시간 + 유료 2시간
        - 주말: 총 2시간 = 무료 1시간 + 주말/유료 1시간
        """
        applications = []
        period_type = "평일" if is_weekday else "주말"
        
        print(f"\n{'='*60}")
        print(f"[@/rules 기준] {period_type} 쿠폰 계산 - 시간 기반 부족분 계산")
        print(f"{'='*60}")
        
        # @/rules 지침에 따른 목표 시간 설정
        if is_weekday:
            target_hours = 3  # 평일 3시간
        else:
            target_hours = 2  # 주말 2시간
        
        print(f"[규칙] {period_type} 목표: 총 {target_hours}시간")
        
        # 현재 적용된 시간 계산 (시간 단위)
        current_free_hours = 0
        current_paid_hours = 0
        current_weekend_hours = 0
        
        for rule in self.coupon_rules:
            used_count = my_history.get(rule.coupon_key, 0)
            if used_count > 0:
                used_hours = used_count * (rule.duration_minutes / 60.0)
                if rule.coupon_type == CouponType.FREE:
                    current_free_hours += used_hours
                elif rule.coupon_type == CouponType.PAID:
                    current_paid_hours += used_hours
                elif rule.coupon_type == CouponType.WEEKEND:
                    current_weekend_hours += used_hours
                print(f"[현재상태] {rule.coupon_key}: {used_count}개 = {used_hours:.1f}시간")
        
        total_current_hours = current_free_hours + current_paid_hours + current_weekend_hours
        print(f"[현재상태] 무료: {current_free_hours:.1f}시간, 유료: {current_paid_hours:.1f}시간, 주말: {current_weekend_hours:.1f}시간")
        print(f"[현재상태] 총 적용된 시간: {total_current_hours:.1f}시간")
        
        print(f"\n{'-'*50}")
        print(f"1단계: 무료 쿠폰 계산 (룰파일 4.4)")
        print(f"{'-'*50}")
        
        # 1. 무료 쿠폰 계산 (@/rules 로직)
        free_rules = [rule for rule in self.coupon_rules if rule.coupon_type == CouponType.FREE]
        free_apply_hours = 0
        
        for rule in free_rules:
            # @/rules: free_apply = 0 if total_free_used > 0 else max(0, 1 - my_free)
            total_free_used = total_history.get(rule.coupon_key, 0)
            my_free_used_count = my_history.get(rule.coupon_key, 0)
            my_free_used_hours = my_free_used_count * (rule.duration_minutes / 60.0)
            
            if total_free_used > 0:
                print(f"[무료쿠폰] {rule.coupon_key} 전체 이력에서 이미 사용됨. 스킵.")
                free_apply_count = 0
            else:
                # 1시간 기준으로 계산: max(0, 1 - my_free_hours)
                free_need_hours = max(0, 1.0 - my_free_used_hours)
                free_apply_count = int(free_need_hours / (rule.duration_minutes / 60.0)) if free_need_hours > 0 else 0
                
                if free_apply_count > 0:
                    available = available_coupons.get(rule.coupon_name, 0)
                    free_apply_count = min(free_apply_count, available)
                    
                    if free_apply_count > 0:
                        free_apply_hours = free_apply_count * (rule.duration_minutes / 60.0)
                        print(f"[무료쿠폰] {rule.coupon_key} {free_apply_count}개 적용 예정 ({free_apply_hours:.1f}시간)")
                        
                        applications.append(CouponApplication(
                            coupon_name=rule.coupon_name,
                            coupon_type=rule.coupon_type,
                            count=free_apply_count
                        ))
                    else:
                        print(f"[무료쿠폰] {rule.coupon_key} 보유 쿠폰 부족")
                else:
                    print(f"[무료쿠폰] {rule.coupon_key} 이미 충분히 사용됨")
        
        print(f"\n{'-'*50}")
        print(f"2단계: {period_type} 쿠폰 계산 (룰파일 4.2/4.3)")
        print(f"{'-'*50}")
        
        # 2. 유료/주말 쿠폰 계산 (@/rules 로직)
        if is_weekday:
            target_coupon_types = [CouponType.PAID]
        else:
            # 주말: 먼저 WEEKEND 타입 확인, 없으면 PAID 타입 사용
            weekend_rules = [rule for rule in self.coupon_rules if rule.coupon_type == CouponType.WEEKEND]
            if weekend_rules:
                target_coupon_types = [CouponType.WEEKEND]
                print(f"[주말쿠폰] WEEKEND 타입 쿠폰 발견: {len(weekend_rules)}개")
            else:
                target_coupon_types = [CouponType.PAID]
                print(f"[주말쿠폰] WEEKEND 타입 없음. PAID 타입으로 대체")
        
        for target_type in target_coupon_types:
            target_rules = [rule for rule in self.coupon_rules if rule.coupon_type == target_type]
            
            for rule in target_rules:
                # @/rules: paid_apply = total_needed - (my_paid + free_apply)
                if is_weekday:
                    # 평일: paid_apply = 3 - (current_free_hours + current_paid_hours + free_apply_hours)
                    paid_need_hours = target_hours - (current_free_hours + current_paid_hours + free_apply_hours)
                else:
                    # 주말: weekend_apply = 2 - (current_free_hours + current_weekend_hours + free_apply_hours)
                    if target_type == CouponType.WEEKEND:
                        paid_need_hours = target_hours - (current_free_hours + current_weekend_hours + free_apply_hours)
                    else:
                        # WEEKEND가 없어서 PAID 사용하는 경우
                        paid_need_hours = target_hours - (current_free_hours + current_paid_hours + free_apply_hours)
                
                if paid_need_hours <= 0:
                    print(f"[{target_type.value}쿠폰] {rule.coupon_key} 이미 충분히 적용됨. 스킵.")
                    continue
                
                # 필요한 개수 계산
                paid_apply_count = int((paid_need_hours * 60) / rule.duration_minutes + 0.99)  # 올림
                available = available_coupons.get(rule.coupon_name, 0)
                paid_apply_count = min(paid_apply_count, available)
                
                if paid_apply_count > 0:
                    paid_apply_hours = paid_apply_count * (rule.duration_minutes / 60.0)
                    print(f"[{target_type.value}쿠폰] {rule.coupon_key} {paid_apply_count}개 적용 예정 ({paid_apply_hours:.1f}시간)")
                    print(f"[{target_type.value}쿠폰] 계산: 목표 {target_hours}시간 - 기존무료 {current_free_hours:.1f}시간 - 기존유료 {current_paid_hours if target_type == CouponType.PAID else current_weekend_hours:.1f}시간 = 부족 {paid_need_hours:.1f}시간")
                    
                    applications.append(CouponApplication(
                        coupon_name=rule.coupon_name,
                        coupon_type=rule.coupon_type,
                        count=paid_apply_count
                    ))
                else:
                    print(f"[{target_type.value}쿠폰] {rule.coupon_key} 보유 쿠폰 부족: 필요 {paid_apply_count}개, 보유 {available}개")
        
        print(f"\n{'='*60}")
        print(f"[최종결과] 적용할 쿠폰 총 {len(applications)}개")
        print(f"{'='*60}")
        
        total_apply_hours = 0
        for app in applications:
            # 해당 쿠폰의 duration_minutes 찾기
            rule_duration = next((rule.duration_minutes for rule in self.coupon_rules 
                                if rule.coupon_name == app.coupon_name), 0)
            apply_hours = app.count * (rule_duration / 60.0)
            total_apply_hours += apply_hours
            
            print(f">>>>> 최종 적용할 쿠폰: {app.coupon_name} {app.count}개 ({apply_hours:.1f}시간)")
        
        final_total_hours = total_current_hours + total_apply_hours
        
        print(f"\n[최종확인] 현재 적용된 시간: {total_current_hours:.1f}시간")
        print(f"[최종확인] 추가 적용할 시간: {total_apply_hours:.1f}시간")
        print(f"[최종확인] 적용 후 총시간: {final_total_hours:.1f}시간")
        print(f"[최종확인] {period_type} 목표달성: {'✅ 달성' if final_total_hours >= target_hours else '❌ 미달성'}")
        print(f"{'='*60}\n")
        
        return [app for app in applications if app.is_valid()] 