"""
쿠폰 도메인 모델
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import datetime


class CouponType(Enum):
    """쿠폰 타입"""
    FREE = "free"
    PAID = "paid"
    WEEKEND = "weekend"


class CouponStatus(Enum):
    """쿠폰 상태"""
    AVAILABLE = "available"
    USED = "used"
    EXPIRED = "expired"


@dataclass
class Coupon:
    """쿠폰 엔티티"""
    id: str
    name: str
    coupon_type: CouponType
    duration_minutes: int
    store_id: str
    status: CouponStatus = CouponStatus.AVAILABLE
    created_at: Optional[datetime] = None
    used_at: Optional[datetime] = None
    
    def is_available(self) -> bool:
        """쿠폰 사용 가능 여부"""
        return self.status == CouponStatus.AVAILABLE
    
    def use(self) -> None:
        """쿠폰 사용 처리"""
        if not self.is_available():
            raise ValueError(f"쿠폰을 사용할 수 없습니다. 현재 상태: {self.status}")
        
        self.status = CouponStatus.USED
        self.used_at = datetime.now()


@dataclass
class CouponHistory:
    """쿠폰 사용 이력"""
    store_id: str
    vehicle_id: str
    my_history: dict[str, int]  # 내 매장 사용 이력
    total_history: dict[str, int]  # 전체 매장 사용 이력
    available_coupons: dict[str, int]  # 사용 가능한 쿠폰
    
    def get_my_usage(self, coupon_name: str) -> int:
        """내 매장에서의 특정 쿠폰 사용 횟수"""
        return self.my_history.get(coupon_name, 0)
    
    def get_total_usage(self, coupon_name: str) -> int:
        """전체 매장에서의 특정 쿠폰 사용 횟수"""
        return self.total_history.get(coupon_name, 0)
    
    def get_available_count(self, coupon_name: str) -> int:
        """사용 가능한 특정 쿠폰 개수"""
        return self.available_coupons.get(coupon_name, 0)


@dataclass
class CouponApplication:
    """쿠폰 적용 요청"""
    coupon_name: str
    coupon_type: CouponType
    count: int
    
    def is_valid(self) -> bool:
        """유효한 적용 요청인지 확인"""
        return self.count > 0 