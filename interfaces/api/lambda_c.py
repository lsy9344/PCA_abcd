"""
C매장 전용 Lambda 핸들러
05_store_routing.mdc 규칙에 따른 매장별 Lambda 구현
"""
import json
import asyncio
import time
import threading
from typing import Dict, Any

from core.application.dto.automation_dto import AutomationRequest, AutomationResponse
from infrastructure.config.config_manager import ConfigManager
from infrastructure.factories.automation_factory import AutomationFactory


# 전역 팩토리 (Lambda 컨테이너 재사용을 위해)
_config_manager = None
_automation_factory = None
_active_requests = {}  # 활성 요청 추적: {request_key: {'start_time': timestamp, 'thread_id': id}}
_request_lock = threading.Lock()  # 활성 요청 접근에 대한 락


def get_automation_factory() -> AutomationFactory:
    """자동화 팩토리 싱글톤 조회 (스레드 안전)"""
    global _config_manager, _automation_factory
    
    if _automation_factory is None:
        print("[INFO] 자동화 팩토리 초기화 중...")
        try:
            _config_manager = ConfigManager()
            _automation_factory = AutomationFactory(_config_manager)
            print("[INFO] 자동화 팩토리 초기화 완료")
        except Exception as e:
            print(f"[ERROR] 자동화 팩토리 초기화 실패: {str(e)}")
            raise
    
    return _automation_factory


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """C매장 전용 Lambda 핸들러"""
    request_key = None
    try:
        # 요청 파라미터 추출
        body = json.loads(event.get('body', '{}')) if isinstance(event.get('body'), str) else event.get('body', {})
        
        # C매장 고정, 차량번호만 받음
        store_id = "C"
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
        
        # 중복 요청 방지 (스레드 세이프)
        request_key = f"{store_id}_{vehicle_number}"
        current_time = time.time()
        thread_id = threading.get_ident()
        
        with _request_lock:
            # 활성 요청 상태 확인
            if request_key in _active_requests:
                active_request = _active_requests[request_key]
                elapsed_time = current_time - active_request['start_time']
                
                # 5분 이상 경과한 요청은 타임아웃으로 간주하고 제거
                if elapsed_time > 300:  # 5분
                    print(f"[WARNING] 오래된 요청 타임아웃 제거: {request_key} (경과시간: {elapsed_time:.1f}초)")
                    del _active_requests[request_key]
                else:
                    return {
                        'statusCode': 409,  # Conflict
                        'body': json.dumps({
                            'success': False,
                            'error': f'동일한 요청이 이미 처리 중입니다: {request_key} (경과시간: {elapsed_time:.1f}초)',
                            'request_id': request_key,
                            'active_thread_id': active_request['thread_id']
                        }, ensure_ascii=False)
                    }
            
            # 활성 요청으로 등록
            _active_requests[request_key] = {
                'start_time': current_time,
                'thread_id': thread_id
            }
            print(f"[INFO] 요청 시작: {request_key} (스레드 ID: {thread_id})")
        
        # 자동화 실행
        request = AutomationRequest(
            store_id=store_id,
            vehicle_number=vehicle_number
        )
        
        response: AutomationResponse = asyncio.run(execute_automation(request))
        
        # 응답 상태 코드 결정
        status_code = 200 if response.success else 422
        
        elapsed_time = time.time() - current_time
        print(f"[INFO] 요청 완료: {request_key}, 성공: {response.success} (처리시간: {elapsed_time:.1f}초)")
            
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
        error_msg = str(e)
        print(f"[ERROR] Lambda 핸들러 오류: {error_msg}")
        
        # 예상치 못한 서버 장애
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': f'C매장 Lambda 핸들러에서 예상치 못한 오류가 발생했습니다: {error_msg}',
                'request_id': request_key
            }, ensure_ascii=False)
        }
    
    finally:
        # 활성 요청에서 제거 (스레드 세이프)
        if request_key:
            with _request_lock:
                if request_key in _active_requests:
                    elapsed_time = time.time() - _active_requests[request_key]['start_time']
                    del _active_requests[request_key]
                    print(f"[INFO] 요청 정리: {request_key} (총 처리시간: {elapsed_time:.1f}초)")


async def execute_automation(request: AutomationRequest) -> AutomationResponse:
    """C매장 자동화 실행"""
    use_case = None
    try:
        factory = get_automation_factory()
        use_case = factory.create_apply_coupon_use_case(request.store_id)
        
        print(f"[INFO] 자동화 실행 시작: {request.store_id}_{request.vehicle_number}")
        response = await use_case.execute(request)
        print(f"[INFO] 자동화 실행 완료: {request.store_id}_{request.vehicle_number}")
        
        return response
        
    except Exception as e:
        print(f"[ERROR] 자동화 실행 오류: {str(e)}")
        # 오류 발생 시도 응답 객체 반환
        return AutomationResponse(
            request_id=request.request_id,
            success=False,
            store_id=request.store_id,
            vehicle_number=request.vehicle_number,
            applied_coupons=[],
            error_message=str(e)
        )
    
    finally:
        # use_case에서 cleanup이 이미 수행되지만 추가 안전 장치
        try:
            if use_case and hasattr(use_case, '_store_repository'):
                if hasattr(use_case._store_repository, 'cleanup'):
                    await use_case._store_repository.cleanup()
        except Exception as cleanup_error:
            print(f"[WARNING] 추가 cleanup 실패: {str(cleanup_error)}")
