"""매장 어댑터 표준 인터페이스"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from core.domain.models.coupon import CouponHistory, CouponApplication


class StoreAdapter(ABC):
    """매장 크롤러를 위한 표준 인터페이스"""
    
    @abstractmethod
    async def start(self) -> None:
        """브라우저/컨텍스트 초기화"""
        pass
    
    @abstractmethod
    async def login(self) -> bool:
        """로그인 수행"""
        pass
    
    @abstractmethod
    async def search_vehicle(self, car_number: str) -> bool:
        """차량 검색"""
        pass
    
    @abstractmethod
    async def get_coupon_history(self, car_number: str) -> CouponHistory:
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