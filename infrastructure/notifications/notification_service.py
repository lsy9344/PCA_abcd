"""
알림 서비스
"""
from abc import ABC, abstractmethod
from core.application.dto.automation_dto import ErrorContext


class NotificationService(ABC):
    """알림 서비스 인터페이스"""
    
    @abstractmethod
    async def send_error_notification(self, error_context: ErrorContext) -> bool:
        """에러 알림 전송"""
        pass
    
    @abstractmethod
    async def send_success_notification(self, message: str, store_id: str) -> bool:
        """성공 알림 전송"""
        pass 