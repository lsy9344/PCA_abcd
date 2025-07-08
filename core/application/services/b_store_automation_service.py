"""
B 매장 전용 자동화 서비스
"""
from datetime import datetime
from typing import Dict, Any

from ..dto.automation_dto import AutomationRequest, AutomationResponse, ErrorContext
from infrastructure.web_automation.store_crawlers.b_store_crawler import BStoreCrawler
from core.domain.models.b_discount_calculator import BDiscountCalculator
from core.domain.models.vehicle import Vehicle
from infrastructure.config.config_manager import ConfigManager
from infrastructure.notifications.notification_service import NotificationService
from infrastructure.logging.structured_logger import StructuredLogger
from shared.utils.date_utils import DateUtils


class BStoreAutomationService:
    """B 매장 전용 자동화 서비스"""
    
    def __init__(self,
                 config_manager: ConfigManager,
                 notification_service: NotificationService,
                 logger: StructuredLogger):
        self._config_manager = config_manager
        self._notification_service = notification_service
        self._logger = logger
        
        # B 매장 설정 로드
        self._store_config = config_manager.get_store_config("B")
        self._playwright_config = config_manager.get_playwright_config()
        
        # B 매장 전용 할인 계산기 생성
        discount_policy = config_manager.get_discount_policy("B")
        coupon_rules = config_manager.get_coupon_rules("B")
        self._discount_calculator = BDiscountCalculator(discount_policy, coupon_rules)
        
        # B 매장 크롤러 생성
        self._crawler = BStoreCrawler(
            self._store_config,
            self._playwright_config,
            logger
        )
    
    async def execute(self, request: AutomationRequest) -> AutomationResponse:
        """B 매장 자동화 실행"""
        try:
            # 1. 차량 정보 생성
            vehicle = Vehicle(number=request.vehicle_number)
            
            # 2. 로그인
            login_success = await self._crawler.login()
            if not login_success:
                raise Exception("로그인 실패")
            
            # 3. 차량 검색
            search_success = await self._crawler.search_vehicle(vehicle)
            if not search_success:
                raise Exception("차량 검색 실패")
            
            # 4. 쿠폰 이력 조회
            coupon_history = await self._crawler.get_coupon_history(vehicle)
            
            # 5. 요일 판단
            is_weekday = DateUtils.is_weekday(datetime.now())
            
            # 6. B 매장 특수 규칙으로 할인 계산
            applications = self._discount_calculator.calculate_required_coupons(
                my_history=coupon_history.my_usage_history,
                total_history=coupon_history.total_usage_history,
                available_coupons=coupon_history.available_coupons,
                is_weekday=is_weekday
            )
            
            # 7. 쿠폰 적용
            if applications:
                apply_success = await self._crawler.apply_coupons(applications)
                if not apply_success:
                    raise Exception("쿠폰 적용 실패")
                    
                # 성공 메시지
                applied_summary = []
                for app in applications:
                    if app.count > 0:
                        applied_summary.append(f"{app.coupon_name}: {app.count}개")
                
                success_message = f"B 매장 쿠폰 적용 완료: {', '.join(applied_summary)}"
            else:
                success_message = "B 매장: 적용할 쿠폰이 없습니다"
            
            return AutomationResponse(
                success=True,
                store_id="B",
                vehicle_number=request.vehicle_number,
                message=success_message,
                applied_coupons=[{
                    'name': app.coupon_name,
                    'count': app.count,
                    'type': app.coupon_type.value
                } for app in applications],
                execution_time=datetime.now()
            )
            
        except Exception as e:
            # 실패 시 텔레그램 알림
            await self._notification_service.send_failure_notification(
                store_id="B",
                vehicle_number=request.vehicle_number,
                error_message=str(e),
                error_context=ErrorContext(
                    step="B매장 자동화",
                    details=str(e),
                    timestamp=datetime.now()
                )
            )
            
            return AutomationResponse(
                success=False,
                store_id="B",
                vehicle_number=request.vehicle_number,
                message=f"B 매장 자동화 실패: {str(e)}",
                applied_coupons=[],
                execution_time=datetime.now(),
                error_context=ErrorContext(
                    step="B매장 자동화",
                    details=str(e),
                    timestamp=datetime.now()
                )
            )
            
        finally:
            # 리소스 정리
            await self._crawler.cleanup() 