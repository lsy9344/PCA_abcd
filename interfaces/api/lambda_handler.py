"""
AWS Lambda 핸들러 - HTTP 응답 코드 수정된 버전
"""
import json
import asyncio
from typing import Dict, Any

from core.application.dto.automation_dto import AutomationRequest, AutomationResponse
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
    """Lambda 핸들러 진입점"""
    try:
        # 요청 파라미터 추출
        body = json.loads(event.get('body', '{}')) if isinstance(event.get('body'), str) else event.get('body', {})
        
        store_id = body.get('store_id') or event.get('store_id')
        vehicle_number = body.get('vehicle_number') or event.get('vehicle_number')
        
        # ✅ 수정: 파라미터 누락도 비즈니스 실패(422)로 처리
        if not store_id or not vehicle_number:
            return {
                'statusCode': 422,
                'body': json.dumps({
                    'success': False,
                    'error': 'store_id와 vehicle_number는 필수 파라미터입니다'
                }, ensure_ascii=False)
            }
        
        # 자동화 실행
        request = AutomationRequest(
            store_id=store_id,
            vehicle_number=vehicle_number
        )
        
        response: AutomationResponse = asyncio.run(execute_automation(request))
        
        # ✅ 수정: response.success 값에 따라 상태 코드를 명확히 분기
        if response.success:
            # 성공 시: 200 OK
            status_code = 200
        else:
            # 비즈니스 로직 실패 시: 422 Unprocessable Entity
            status_code = 422
            
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
        # ✅ 수정: 예상치 못한 서버 장애 시에만 500 Internal Server Error 반환
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': f'Lambda 핸들러에서 예상치 못한 오류가 발생했습니다: {str(e)}'
            }, ensure_ascii=False)
        }


async def execute_automation(request: AutomationRequest) -> AutomationResponse:
    """자동화 실행"""
    factory = get_automation_factory()
    use_case = factory.create_apply_coupon_use_case(request.store_id)
    
    return await use_case.execute(request)
