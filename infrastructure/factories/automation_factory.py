"""
자동화 컴포넌트 팩토리
"""
from typing import Dict, Any

from core.application.use_cases.apply_coupon_use_case import ApplyCouponUseCase
from core.domain.models.discount_policy import DiscountCalculator
from core.domain.repositories.store_repository import StoreRepository
from infrastructure.config.config_manager import ConfigManager
from infrastructure.logging.structured_logger import StructuredLogger
from infrastructure.notifications.notification_service import NotificationService
from infrastructure.notifications.telegram_adapter import TelegramAdapter
from infrastructure.web_automation.store_crawlers.a_store_crawler import AStoreCrawler
from infrastructure.web_automation.store_crawlers.b_store_crawler import BStoreCrawler
from core.domain.models.b_discount_calculator import BDiscountCalculator
from shared.exceptions.automation_exceptions import StoreNotSupportedException


class AutomationFactory:
    """자동화 컴포넌트 팩토리"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self._loggers = {}
        self._notification_service = None
    
    def create_logger(self, name: str) -> StructuredLogger:
        """로거 생성"""
        if name not in self._loggers:
            log_config = self.config_manager.get_logging_config()
            self._loggers[name] = StructuredLogger(name, log_config)
        return self._loggers[name]
    
    def create_notification_service(self) -> NotificationService:
        """알림 서비스 생성"""
        if self._notification_service is None:
            telegram_config = self.config_manager.get_telegram_config()
            logger = self.create_logger("telegram")
            self._notification_service = TelegramAdapter(telegram_config, logger)
        return self._notification_service
    
    def create_store_repository(self, store_id: str) -> StoreRepository:
        """매장 리포지토리 생성"""
        store_config = self.config_manager.get_store_config(store_id)
        playwright_config = self.config_manager.get_playwright_config()
        logger = self.create_logger(f"store_{store_id.lower()}")
        notification_service = self.create_notification_service()
        
        if store_id.upper() == "A":
            return AStoreCrawler(store_config, playwright_config, logger)
        elif store_id.upper() == "B":
            return BStoreCrawler(store_config, playwright_config, logger, notification_service)
        else:
            raise StoreNotSupportedException(f"지원하지 않는 매장입니다: {store_id}")
    
    def create_discount_calculator(self, store_id: str) -> DiscountCalculator:
        """할인 계산기 생성"""
        discount_policy = self.config_manager.get_discount_policy(store_id)
        coupon_rules = self.config_manager.get_coupon_rules(store_id)
        
        if store_id.upper() == "B":
            # B 매장은 30분 쿠폰 2배 보정 규칙 적용
            return BDiscountCalculator(discount_policy, coupon_rules)
        else:
            # A 매장 및 기타 매장은 기본 계산기 사용
            return DiscountCalculator(discount_policy, coupon_rules)
    
    def create_apply_coupon_use_case(self, store_id: str) -> ApplyCouponUseCase:
        """쿠폰 적용 유스케이스 생성"""
        store_repository = self.create_store_repository(store_id)
        discount_calculator = self.create_discount_calculator(store_id)
        notification_service = self.create_notification_service()
        logger = self.create_logger("use_case")
        
        return ApplyCouponUseCase(
            store_repository=store_repository,
            discount_calculator=discount_calculator,
            notification_service=notification_service,
            logger=logger
        ) 