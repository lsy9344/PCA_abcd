"""
D매장 전용 Lambda 핸들러
05_store_routing.mdc 규칙에 따른 매장별 Lambda 구현
"""
import json
import asyncio
from typing import Dict, Any

from core.application.dto.automation_dto import AutomationRequest, AutomationResponse
from core.application.services.d_store_automation_service import DStoreAutomationService
from infrastructure.config.config_manager import ConfigManager
from infrastructure.factories.automation_factory import AutomationFactory


# 전역 팩토리 (Lambda 컨테이너 재사용을 위해)
_config_manager = None
_automation_factory = None


def get_automation_factory() -> AutomationFactory:
    """자동화 팩토리 싱글톤 조회"""
    global _config_manager, _automation_factory
    
    if _automation_factory is None:
        _config_manager = ConfigManager()
        _automation_factory = AutomationFactory(_config_manager)
    
    return _automation_factory


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """D매장 전용 Lambda 핸들러"""
    try:
        # 요청 파라미터 추출
        body = json.loads(event.get('body', '{}')) if isinstance(event.get('body'), str) else event.get('body', {})
        
        # D매장 고정, 차량번호만 받음
        store_id = "D"
        vehicle_number = body.get('vehicle_number') or body.get('car_number') or event.get('vehicle_number') or event.get('car_number')
        
        # 차량번호 필수 검증
        if not vehicle_number:
            return {
                'statusCode': 422,
                'body': json.dumps({
                    'success': False,
                    'error': 'vehicle_number(또는 car_number)는 필수 파라미터입니다'
                }, ensure_ascii=False)
            }
        
        # 자동화 실행
        request = AutomationRequest(
            store_id=store_id,
            vehicle_number=vehicle_number
        )
        
        response: AutomationResponse = asyncio.run(execute_automation(request))
        
        # 응답 상태 코드 결정
        status_code = 200 if response.success else 422
            
        return {
            'statusCode': status_code,
            'body': json.dumps({
                'success': response.success,
                'request_id': response.request_id,
                'store_id': response.store_id,
                'vehicle_number': response.vehicle_number,
                'applied_coupons': response.applied_coupons,
                'error_message': response.error_message,
                'completed_at': response.completed_at.isoformat() if response.completed_at else None
            }, ensure_ascii=False)
        }
        
    except Exception as e:
        # 예상치 못한 서버 장애
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': f'D매장 Lambda 핸들러에서 예상치 못한 오류가 발생했습니다: {str(e)}'
            }, ensure_ascii=False)
        }


async def execute_automation(request: AutomationRequest) -> AutomationResponse:
    """D매장 자동화 실행 - 전용 서비스 사용"""
    factory = get_automation_factory()
    
    # D매장 전용 자동화 서비스 생성
    config_manager = factory.config_manager
    notification_service = factory.create_notification_service()
    logger = factory.create_logger("d_store_automation")
    
    d_store_service = DStoreAutomationService(
        config_manager=config_manager,
        notification_service=notification_service,
        logger=logger
    )
    
    return await d_store_service.execute(request)
