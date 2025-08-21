"""
D 매장 전용 자동화 서비스
- 공통 계산 로직 기반
- 30분 단위 유료 쿠폰 특화 
- 팝업 미출현 특성 반영
"""
from datetime import datetime
from typing import Dict, Any

from ..dto.automation_dto import AutomationRequest, AutomationResponse, ErrorContext
from infrastructure.web_automation.store_crawlers.d_store_crawler import DStoreCrawler
from core.domain.rules.d_discount_rule import DDiscountRule
from core.domain.models.vehicle import Vehicle
from core.domain.models.coupon import CouponApplication
from infrastructure.config.config_manager import ConfigManager
from infrastructure.notifications.notification_service import NotificationService
from infrastructure.logging.structured_logger import StructuredLogger
from shared.utils.date_utils import DateUtils


class DStoreAutomationService:
    """D 매장 전용 자동화 서비스"""
    
    def __init__(self,
                 config_manager: ConfigManager,
                 notification_service: NotificationService,
                 logger: StructuredLogger):
        self._config_manager = config_manager
        self._notification_service = notification_service
        self._logger = logger
        
        # D 매장 설정 로드
        self._store_config = config_manager.get_store_config("D")
        self._playwright_config = config_manager.get_playwright_config()
        
        # D 매장 전용 할인 규칙 생성 (문서 기반 동적 계산)
        self._discount_rule = DDiscountRule()
        
        # D 매장 크롤러 생성
        self._crawler = DStoreCrawler(
            self._store_config,
            self._playwright_config,
            logger,
            notification_service
        )
    
    async def execute(self, request: AutomationRequest) -> AutomationResponse:
        """D 매장 자동화 실행 - 공통 로직 기반"""
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
            
            # 4. 쿠폰 이력 조회 (공통 로직 사용)
            coupon_history = await self._crawler.get_coupon_history(vehicle)
            
            # 디버그: 크롤러에서 받은 데이터 상세 로깅
            self._logger.log_info("🔍 [자동화 서비스] 크롤러에서 받은 쿠폰 이력 데이터:")
            self._logger.log_info(f"   📋 my_history: {coupon_history.my_history}")
            self._logger.log_info(f"   📋 total_history: {coupon_history.total_history}")
            self._logger.log_info(f"   📋 available_coupons: {coupon_history.available_coupons}")
            
            # 디버그: 할인 규칙에 전달할 데이터 확인
            extracted_counts = self._extract_available_counts(coupon_history.available_coupons)
            self._logger.log_info(f"   📊 extracted_counts: {extracted_counts}")
            
            # 5. D 매장 할인 규칙으로 쿠폰 계산 (동적 계산 알고리즘)
            self._logger.log_info("🧮 [자동화 서비스] D 매장 할인 규칙 계산 시작...")
            coupon_decisions = self._discount_rule.decide_coupon_to_apply(
                my_history=coupon_history.my_history,
                total_history=coupon_history.total_history,
                discount_info=extracted_counts
            )
            
            self._logger.log_info(f"📤 [자동화 서비스] 할인 규칙 계산 결과: {coupon_decisions}")
            
            # 6. 쿠폰 적용 요청 생성
            applications = self._create_coupon_applications(coupon_decisions)
            
            # 7. 쿠폰 적용 (D매장 특성: 팝업 미출현)
            if any(app.count > 0 for app in applications):
                apply_success = await self._crawler.apply_coupons(applications)
                if not apply_success:
                    raise Exception("쿠폰 적용 실패")
                    
                # 성공 메시지
                applied_summary = []
                for app in applications:
                    if app.count > 0:
                        applied_summary.append(f"{app.coupon_name}: {app.count}개")
                
                success_message = f"D 매장 쿠폰 적용 완료 (팝업 미출현): {', '.join(applied_summary)}"
            else:
                success_message = "D 매장: 적용할 쿠폰이 없습니다"
            
            return AutomationResponse(
                success=True,
                store_id="D",
                vehicle_number=request.vehicle_number,
                message=success_message,
                applied_coupons=[{
                    'name': app.coupon_name,
                    'count': app.count,
                    'type': 'FREE' if 'FREE' in app.coupon_name else 'PAID'
                } for app in applications],
                execution_time=datetime.now()
            )
            
        except Exception as e:
            # 실패 시 텔레그램 알림
            await self._notification_service.send_failure_notification(
                store_id="D",
                vehicle_number=request.vehicle_number,
                error_message=str(e),
                error_context=ErrorContext(
                    step="D매장 자동화",
                    details=str(e),
                    timestamp=datetime.now()
                )
            )
            
            return AutomationResponse(
                success=False,
                store_id="D",
                vehicle_number=request.vehicle_number,
                message=f"D 매장 자동화 실패: {str(e)}",
                applied_coupons=[],
                execution_time=datetime.now(),
                error_context=ErrorContext(
                    step="D매장 자동화",
                    details=str(e),
                    timestamp=datetime.now()
                )
            )
            
        finally:
            # 리소스 정리
            await self._crawler.cleanup()
    
    def _extract_available_counts(self, available_coupons: Dict[str, Dict[str, int]]) -> Dict[str, int]:
        """보유 쿠폰 정보에서 개수만 추출"""
        result = {}
        for coupon_name, counts in available_coupons.items():
            # 'car' 또는 'total' 중 더 큰 값 사용 (보통 동일)
            result[coupon_name] = max(counts.get('car', 0), counts.get('total', 0))
        return result
    
    def _create_coupon_applications(self, coupon_decisions: Dict[str, int]) -> list:
        """쿠폰 결정 결과를 CouponApplication 객체로 변환"""
        applications = []
        
        # D매장 쿠폰 매핑 (할인 규칙과 일치)
        coupon_mapping = {
            'FREE_1HOUR': '1시간 무료',
            'PAID_30MIN': '30분 유료'
        }
        
        for decision_key, count in coupon_decisions.items():
            if count > 0 and decision_key in coupon_mapping:
                applications.append(CouponApplication(
                    coupon_name=coupon_mapping[decision_key],
                    count=count
                ))
        
        return applications