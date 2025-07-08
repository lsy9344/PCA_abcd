"""
자동화 관련 데이터 전송 객체
"""
from dataclasses import dataclass
from typing import Optional, List, Dict
from datetime import datetime


@dataclass
class AutomationRequest:
    """자동화 요청 DTO"""
    store_id: str
    vehicle_number: str
    request_id: Optional[str] = None
    requested_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.requested_at is None:
            self.requested_at = datetime.now()
        if self.request_id is None:
            self.request_id = f"{self.store_id}_{self.vehicle_number}_{int(self.requested_at.timestamp())}"


@dataclass
class AutomationResponse:
    """자동화 응답 DTO"""
    request_id: str
    success: bool
    store_id: str
    vehicle_number: str
    applied_coupons: List[Dict[str, int]]
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.completed_at is None:
            self.completed_at = datetime.now()


@dataclass
class ErrorContext:
    """에러 컨텍스트 DTO"""
    store_id: str
    vehicle_number: Optional[str]
    error_step: str
    error_message: str
    error_time: datetime
    stack_trace: Optional[str] = None
    
    def to_telegram_message(self) -> str:
        """텔레그램 메시지 형식으로 변환"""
        message = "🚨 쿠폰 자동화 실패 알림 🚨\n\n"
        message += f"1. 실패 원인: [{self.error_step}] {self.error_message}\n"
        if self.vehicle_number:
            message += f"2. 실패 차량번호: {self.vehicle_number}\n"
        message += f"3. 실패 매장: {self.store_id}\n"
        message += f"4. 실패 시간: {self.error_time.strftime('%Y/%m/%d %H:%M:%S')}"
        return message 