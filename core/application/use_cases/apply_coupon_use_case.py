"""
쿠폰 적용 유스케이스
"""
from datetime import datetime
from typing import List
import traceback
import os

from ..dto.automation_dto import AutomationRequest, AutomationResponse, ErrorContext
from core.domain.models.vehicle import Vehicle
from core.domain.models.discount_policy import DiscountCalculator
from core.domain.models.coupon import CouponApplication
from core.domain.repositories.store_repository import StoreRepository
from infrastructure.notifications.notification_service import NotificationService
from infrastructure.logging.structured_logger import StructuredLogger
from shared.utils.date_utils import DateUtils


class ApplyCouponUseCase:
    """쿠폰 적용 유스케이스"""
    
    def __init__(self,
                 store_repository: StoreRepository,
                 discount_calculator: DiscountCalculator,
                 notification_service: NotificationService,
                 logger: StructuredLogger):
        self._store_repository = store_repository
        self._discount_calculator = discount_calculator
        self._notification_service = notification_service
        self._logger = logger
        self.logger = logger  # 추가: logger 속성도 설정
    
    async def execute(self, request: AutomationRequest) -> AutomationResponse:
        """쿠폰 적용 유스케이스 실행"""
        try:
            # 1. Store 인스턴스 생성
            self._logger.info(
                f"[{request.store_id}] 쿠폰 자동화 시작 - "
                f"차량번호: {request.vehicle_number}, "
                f"매장: {request.store_id}"
            )
            
            store_instance = self._store_repository
            
            # 2. 로그인
            login_success = await store_instance.login()
            if not login_success:
                raise Exception("로그인 실패")
            # 로그인 성공 로그 제거 (크롤러에서 이미 처리)

            # 3. 차량 검색
            vehicle = Vehicle(number=request.vehicle_number)
            search_success = await store_instance.search_vehicle(vehicle)
            if not search_success:
                raise Exception(f"차량 검색 실패: {request.vehicle_number}")
            # 차량 검색 성공 로그 제거 (크롤러에서 이미 처리)

            # 4. 쿠폰 이력 조회
            coupon_history = await store_instance.get_coupon_history(vehicle)
            discount_info = coupon_history.available_coupons
            my_history = coupon_history.my_history
            total_history = coupon_history.total_history
            # 쿠폰 조회 성공 로그 제거 (크롤러에서 이미 처리)

            # 5. 할인 계산 (프로덕션에서는 상세 정보 생략)
            current_datetime = datetime.now()
            is_weekday = DateUtils.is_weekday(current_datetime)
            
            # 개발 환경에서만 최소한의 정보 로그
            if os.getenv('ENVIRONMENT', 'development') != 'production':
                my_count = sum(my_history.values()) if my_history else 0
                total_count = sum(total_history.values()) if total_history else 0
                if my_count > 0 or total_count > 0:
                    self._logger.info(f"[{request.store_id}] 쿠폰 이력: 우리 매장 {my_count}건, 전체 {total_count}건")

            # 6. 사용 가능한 쿠폰 개수 계산
            available_coupons = {}
            for coupon_name in discount_info:
                available_coupons[coupon_name] = discount_info[coupon_name].get('car', 0)

            # 7. 할인 계산
            applications = self._discount_calculator.calculate_required_coupons(
                my_history=my_history,
                total_history=total_history,
                available_coupons=available_coupons,
                is_weekday=is_weekday
            )

            # 8. 쿠폰 적용 (적용할 쿠폰이 있는 경우에만 로그)
            actually_applied_coupons = []
            if applications:

                # 쿠폰 적용 실행
                apply_result = await store_instance.apply_coupons(applications)
                
                # apply_result가 리스트인 경우 (실제 적용된 쿠폰 목록)
                if isinstance(apply_result, list):
                    actually_applied_coupons = apply_result
                # apply_result가 boolean인 경우
                elif apply_result:
                    # 성공한 경우 계산된 쿠폰을 적용된 것으로 간주
                    actually_applied_coupons = [
                        {app.coupon_name: app.count} for app in applications if app.count > 0
                    ]
                else:
                    # 실패한 경우
                    raise Exception("쿠폰 적용 실패")
            else:
                self._logger.info(f"[{request.store_id}][쿠폰적용] 적용할 쿠폰이 없습니다")

            # 9. 성공 응답 생성
            # 성공 로그 간소화
            self._logger.info(
                f"[{request.store_id}] 쿠폰 자동화 완료 - "
                f"차량: {request.vehicle_number}, "
                f"적용: {len([app for app in applications if app.count > 0])}종류"
            )

            return AutomationResponse(
                request_id=request.request_id,
                success=True,
                store_id=request.store_id,
                vehicle_number=request.vehicle_number,
                applied_coupons=actually_applied_coupons
            )
            
        except Exception as e:
            error_context = ErrorContext(
                store_id=request.store_id,
                vehicle_number=request.vehicle_number,
                error_step=self._get_current_step(str(e)),
                error_message=str(e),
                error_time=datetime.now(),
                stack_trace=traceback.format_exc()
            )
            
            await self._handle_error(error_context)
            
            return AutomationResponse(
                request_id=request.request_id,
                success=False,
                store_id=request.store_id,
                vehicle_number=request.vehicle_number,
                applied_coupons=[],
                error_message=str(e)
            )
        
        finally:
            await self._store_repository.cleanup()
    
    def _get_current_step(self, error_message: str) -> str:
        """에러 메시지와 현재 단계에서 정확한 단계 추출"""
        # 스택 트레이스에서 더 구체적인 정보 추출
        if "get_coupon_history" in error_message:
            return "쿠폰조회"
        elif "search_vehicle" in error_message:
            return "차량검색"
        elif "login" in error_message:
            return "로그인"
        elif "apply_coupons" in error_message:
            return "쿠폰적용"
        elif "calculate_required_coupons" in error_message:
            return "쿠폰계산"
        # 에러 메시지 내용으로 판단
        elif "로그인" in error_message:
            return "로그인"
        elif "차량 검색" in error_message or "검색된 차량이 없습니다" in error_message:
            return "차량검색"
        elif "쿠폰 이력" in error_message or "쿠폰조회" in error_message:
            return "쿠폰조회"
        elif "쿠폰 적용" in error_message:
            return "쿠폰적용"
        else:
            return "알 수 없음"
    
    async def _handle_error(self, error_context: ErrorContext) -> None:
        """에러 처리"""
        self._logger.error(
            f"[{error_context.store_id}] 자동화 실패: {error_context.error_message}",
            extra={
                "store_id": error_context.store_id,
                "vehicle": error_context.vehicle_number,
                "step": error_context.error_step,
                "stack_trace": error_context.stack_trace
            }
        )
        
        await self._notification_service.send_error_notification(error_context) 