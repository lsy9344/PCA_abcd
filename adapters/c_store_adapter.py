"""C매장 어댑터"""

from typing import List
from adapters.store_adapter import StoreAdapter
from core.domain.models.vehicle import Vehicle
from core.domain.models.coupon import CouponHistory, CouponApplication
from infrastructure.web_automation.store_crawlers.c_store_crawler import CStoreCrawler


class CStoreAdapter(StoreAdapter):
    """C매장 크롤러를 표준 인터페이스로 감싸는 어댑터"""
    
    def __init__(self, store_config, playwright_config, structured_logger, notification_service=None):
        self.crawler = CStoreCrawler(
            store_config=store_config,
            playwright_config=playwright_config, 
            structured_logger=structured_logger,
            notification_service=notification_service
        )
        self._vehicle = None
    
    async def start(self) -> None:
        """브라우저/컨텍스트 초기화"""
        # CStoreCrawler는 login()에서 브라우저를 초기화하므로 여기서는 패스
        pass
    
    async def login(self) -> bool:
        """로그인 수행"""
        return await self.crawler.login()
    
    async def search_vehicle(self, car_number: str) -> bool:
        """차량 검색 - 내부적으로 Vehicle 객체로 변환하여 크롤러에 전달"""
        self._vehicle = Vehicle(number=car_number)
        return await self.crawler.search_vehicle(self._vehicle)
    
    async def get_coupon_history(self, car_number: str) -> CouponHistory:
        """쿠폰 이력 조회 - 내부적으로 Vehicle 객체로 변환하여 크롤러에 전달"""
        if not self._vehicle or self._vehicle.number != car_number:
            self._vehicle = Vehicle(number=car_number)
        return await self.crawler.get_coupon_history(self._vehicle)
    
    async def apply_coupons(self, applications: List[CouponApplication]) -> bool:
        """쿠폰 적용"""
        return await self.crawler.apply_coupons(applications)
    
    async def cleanup(self) -> None:
        """리소스 정리"""
        await self.crawler.cleanup()