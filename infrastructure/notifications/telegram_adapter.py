"""
텔레그램 알림 어댑터
"""
import asyncio
import aiohttp
from typing import Dict, Any

from infrastructure.notifications.notification_service import NotificationService
from core.application.dto.automation_dto import ErrorContext
from infrastructure.logging.structured_logger import StructuredLogger


class TelegramAdapter(NotificationService):
    """텔레그램 알림 어댑터"""
    
    def __init__(self, telegram_config: Dict[str, Any], logger: StructuredLogger):
        self.bot_token = telegram_config['bot_token']
        self.chat_id = telegram_config['chat_id']
        self.max_retries = telegram_config.get('max_retries', 3)
        self.retry_delay = telegram_config.get('retry_delay', 1.0)
        self.logger = logger
        
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    async def send_error_notification(self, error_context: ErrorContext) -> bool:
        """에러 알림 전송"""
        message = error_context.to_telegram_message()
        return await self._send_message(message)
    
    async def send_success_notification(self, message: str, store_id: str) -> bool:
        """성공 알림 전송"""
        formatted_message = f"✅ [{store_id}매장] {message}"
        return await self._send_message(formatted_message)
    
    async def _send_message(self, message: str) -> bool:
        """메시지 전송 (재시도 포함)"""
        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    url = f"{self.base_url}/sendMessage"
                    data = {
                        'chat_id': self.chat_id,
                        'text': message,
                        'parse_mode': 'HTML'
                    }
                    
                    async with session.post(url, data=data) as response:
                        if response.status == 200:
                            self.logger.info("텔레그램 알림 전송 성공")
                            return True
                        else:
                            error_text = await response.text()
                            self.logger.warning(
                                f"텔레그램 알림 전송 실패 (시도 {attempt + 1}/{self.max_retries})",
                                extra={"status": response.status, "error": error_text}
                            )
            
            except Exception as e:
                self.logger.warning(
                    f"텔레그램 알림 전송 예외 (시도 {attempt + 1}/{self.max_retries}): {str(e)}"
                )
            
            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.retry_delay)
        
        self.logger.error("텔레그램 알림 전송 최종 실패")
        return False