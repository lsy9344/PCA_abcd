"""
AWS CloudWatch Logs 비용 최적화를 위한 로거 시스템

주요 기능:
1. 환경별 로그 레벨 자동 설정 (프로덕션: WARNING, 개발: INFO)
2. 간소화된 에러 코드 시스템
3. 텔레그램 알림과 로그 기록 분리
4. 비용 절감을 위한 최적화된 로깅
5. 기존 코드와의 호환성 유지
"""

import logging
import os
from typing import Optional, Dict, Any
from enum import Enum


class ErrorCode(Enum):
    """간소화된 에러 코드 시스템 (CloudWatch Logs 비용 절감용)"""
    FAIL_AUTH = "FAIL_AUTH"           # 로그인 실패
    NO_VEHICLE = "NO_VEHICLE"         # 차량 검색 결과 없음
    FAIL_SEARCH = "FAIL_SEARCH"       # 차량 검색 실패
    FAIL_PARSE = "FAIL_PARSE"         # 쿠폰 이력 파싱 실패
    FAIL_APPLY = "FAIL_APPLY"         # 쿠폰 적용 실패
    FAIL_NETWORK = "FAIL_NETWORK"     # 네트워크 오류
    FAIL_TIMEOUT = "FAIL_TIMEOUT"     # 타임아웃 오류
    FAIL_SETUP = "FAIL_SETUP"         # 설정/초기화 실패
    FAIL_TEST = "FAIL_TEST"           # 테스트 실행 실패
    SUCCESS = "SUCCESS"               # 성공


class OptimizedLogger:
    """AWS CloudWatch Logs 비용 최적화 로거"""
    
    def __init__(self, name: str, store_name: str = ""):
        self.logger = logging.getLogger(name)
        self.store_name = store_name
        self.environment = os.getenv('ENVIRONMENT', 'development')
        
        # 환경별 로그 레벨 자동 설정
        if self.environment == 'production':
            self.logger.setLevel(logging.WARNING)
        else:
            self.logger.setLevel(logging.INFO)
        
        # 중복 핸들러 방지: 이미 핸들러가 있으면 추가하지 않음
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            
        # 부모 로거로의 전파 방지 (중복 출력 방지)
        self.logger.propagate = False
    
    def should_log_info(self) -> bool:
        """개발 환경에서만 INFO 로그를 기록할지 여부 반환"""
        return self.environment != 'production'
    
    def log_error(self, *args, **kwargs) -> Dict[str, Any]:
        """
        에러 로그 기록 (기존 코드와 호환성 유지)
        
        두 가지 시그니처 지원:
        1. 새로운 방식: log_error(error_code, step, telegram_message=None)
        2. 기존 방식: log_error(store, step, code, message, extra=None)
        """
        if len(args) >= 4:
            # 기존 방식: log_error("A", "차량검색", "FAIL_SEARCH", "메시지")
            store, step, code, message = args[0], args[1], args[2], args[3]
            
            # CloudWatch Logs에는 간소화된 메시지만 기록
            log_message = f"[{store}][{step}] {code}"
            self.logger.error(log_message)
            
            # 텔레그램 메시지는 별도 처리
            if message and self.environment != 'production':
                self.logger.debug(f"Details: {message}")
            
            return {
                "store": store,
                "step": step, 
                "code": code,
                "message": message
            }
        
        elif len(args) >= 2:
            # 새로운 방식: log_error(error_code, step, telegram_message=None)
            error_code = args[0]
            step = args[1]
            telegram_message = args[2] if len(args) > 2 else kwargs.get('telegram_message')
            
            # ErrorCode enum 처리
            if hasattr(error_code, 'value'):
                code_value = error_code.value
            else:
                code_value = str(error_code)
                
            # CloudWatch Logs에는 간소화된 메시지만 기록
            log_message = f"[{self.store_name}][{step}] {code_value}"
            self.logger.error(log_message)
            
            # 텔레그램 메시지는 별도 처리
            if telegram_message and self.environment != 'production':
                self.logger.debug(f"Telegram message: {telegram_message}")
            
            return {
                "store": self.store_name,
                "step": step,
                "code": code_value,
                "message": telegram_message
            }
        
        else:
            raise ValueError("log_error requires at least 2 arguments")
    
    def log_success(self, step: str, details: Optional[str] = None) -> None:
        """성공 로그 기록"""
        if self.environment == 'production':
            # 프로덕션에서는 성공 로그 최소화
            return
        
        log_message = f"[{self.store_name}][{step}] SUCCESS"
        if details:
            log_message += f" - {details}"
        self.logger.info(log_message)
    
    def log_info(self, message: str) -> None:
        """정보 로그 기록 (개발 환경에서만)"""
        if self.environment != 'production':
            self.logger.info(f"[{self.store_name}] {message}")
    
    def log_warning(self, message: str) -> None:
        """경고 로그 기록"""
        self.logger.warning(f"[{self.store_name}] {message}")


class ErrorContext:
    """에러 컨텍스트 정보 (텔레그램 알림용)"""
    
    def __init__(self, store_name: str, car_number: str, step: str):
        self.store_name = store_name
        self.car_number = car_number
        self.step = step
        self.timestamp = None
        self.error_message = None
    
    def set_error(self, error_message: str) -> None:
        """에러 정보 설정"""
        import datetime
        self.error_message = error_message
        self.timestamp = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    
    def get_telegram_message(self) -> str:
        """텔레그램 알림용 메시지 생성"""
        return f"""🚨 쿠폰 자동화 실패 🚨

매장: {self.store_name}
차량: {self.car_number}
단계: {self.step}
시간: {self.timestamp}
원인: {self.error_message}"""


def get_optimized_logger(name: str, store_name: str = "") -> OptimizedLogger:
    """최적화된 로거 인스턴스 생성"""
    return OptimizedLogger(name, store_name)


# 사용 예시
if __name__ == "__main__":
    # 개발 환경 테스트
    os.environ['ENVIRONMENT'] = 'development'
    logger = get_optimized_logger("test", "A")
    
    logger.log_info("테스트 시작")
    logger.log_success("로그인", "성공적으로 로그인됨")
    
    # 기존 방식 테스트
    logger.log_error("A", "차량검색", "FAIL_SEARCH", "차량을 찾을 수 없습니다")
    
    # 새로운 방식 테스트  
    logger.log_error(ErrorCode.FAIL_PARSE, "쿠폰조회", "셀렉터를 찾을 수 없습니다")
    
    # 프로덕션 환경 테스트
    os.environ['ENVIRONMENT'] = 'production'
    prod_logger = get_optimized_logger("prod_test", "B")
    
    prod_logger.log_info("이 메시지는 프로덕션에서 기록되지 않음")
    prod_logger.log_error(ErrorCode.FAIL_AUTH, "로그인", "인증 실패") 