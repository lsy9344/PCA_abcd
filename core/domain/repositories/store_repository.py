"""
매장 리포지토리 인터페이스
"""
from abc import ABC, abstractmethod
from typing import List
from ..models.coupon import CouponHistory, CouponApplication
from ..models.vehicle import Vehicle


class StoreRepository(ABC):
    """매장 데이터 접근 인터페이스"""
    
    @abstractmethod
    async def login(self) -> bool:
        """로그인 수행"""
        pass
    
    @abstractmethod
    async def search_vehicle(self, vehicle: Vehicle) -> bool:
        """차량 검색"""
        pass
    
    @abstractmethod
    async def get_coupon_history(self, vehicle: Vehicle) -> CouponHistory:
        """쿠폰 이력 조회"""
        pass
    
    @abstractmethod
    async def apply_coupons(self, applications: List[CouponApplication]) -> bool:
        """쿠폰 적용"""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """리소스 정리"""
        pass 