"""
B 매장 Store 클래스 - 실제 테스트 검증된 버전
새로운 크롤러와 할인 규칙을 사용
"""
from typing import Dict
from playwright.async_api import async_playwright
from .base_store import BaseStore
from ..rules.b_discount_rule import BDiscountRule
from ...infrastructure.web_automation.store_crawlers.b_store_crawler import BStoreCrawler


class BStore(BaseStore):
    """B 매장 - 실제 테스트 검증된 버전"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.store_id = "B"
        self.discount_rule = BDiscountRule()
        self.crawler = BStoreCrawler(config)
    
    async def run(self, car_number: str) -> bool:
        """B 매장 자동화 실행"""
        try:
            self.logger.info(f"🚀 B 매장 자동화 시작 - 차량번호: {car_number}")
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,  # Lambda 환경에서는 headless 필수
        args=[
            '--no-sandbox',                    # Lambda 보안 정책 필수
            '--disable-dev-shm-usage',        # 메모리 최적화  
            '--disable-gpu',                   # GPU 비활성화
            '--disable-web-security',          # CORS 우회
            '--disable-features=VizDisplayCompositor',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--single-process',                # Lambda 프로세스 최적화
            '--no-zygote'                      # Lambda 환경 최적화
        ]
    )
                page = await browser.new_page()
                
                try:
                    # 1. 로그인
                    if not await self.login(page):
                        return False
                    
                    # 2. 차량 검색
                    if not await self.search_car(page, car_number):
                        return False
                    
                    # 3. 쿠폰 이력 조회
                    my_history, total_history, discount_info = await self.get_coupon_history(page)
                    
                    # 4. 적용할 쿠폰 결정
                    coupons_to_apply = self.discount_rule.decide_coupon_to_apply(
                        my_history, total_history, discount_info
                    )
                    
                    # 5. 쿠폰 적용
                    if coupons_to_apply:
                        success = await self.apply_coupons(page, coupons_to_apply)
                        if success:
                            self.logger.info("✅ B 매장 자동화 완료")
                            return True
                        else:
                            self.logger.error("❌ 쿠폰 적용 실패")
                            return False
                    else:
                        self.logger.info("ℹ️ 적용할 쿠폰이 없음")
                        return True
                
                finally:
                    await browser.close()
        
        except Exception as e:
            self.logger.error(f"❌ B 매장 자동화 중 오류: {str(e)}")
            return False
    
    async def login(self, page) -> bool:
        """로그인"""
        return await self.crawler.login(page)
    
    async def search_car(self, page, car_number: str) -> bool:
        """차량 검색"""
        return await self.crawler.search_car(page, car_number)
    
    async def get_coupon_history(self, page):
        """쿠폰 이력 조회"""
        return await self.crawler.get_coupon_history(page)
    
    async def apply_coupons(self, page, coupons_to_apply: Dict[str, int]) -> bool:
        """쿠폰 적용"""
        return await self.crawler.apply_coupons(page, coupons_to_apply) 