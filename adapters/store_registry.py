"""매장 레지스트리"""

from typing import Dict, Type
from adapters.store_adapter import StoreAdapter
from adapters.d_store_adapter import DStoreAdapter
from adapters.a_store_adapter import AStoreAdapter
from adapters.b_store_adapter import BStoreAdapter
from adapters.c_store_adapter import CStoreAdapter
from adapters.e_store_adapter import EStoreAdapter
from infrastructure.config.loader import load_runtime_options, load_telegram_config
from infrastructure.config.config_manager import ConfigManager
from infrastructure.logging.structured_logger import StructuredLogger
from infrastructure.notifications.telegram_adapter import TelegramAdapter


def get_store_adapter(store_id: str) -> StoreAdapter:
    """매장 ID로 어댑터 인스턴스 생성"""
    store_id_upper = store_id.upper()
    
    # 설정 로드
    config_manager = ConfigManager()
    store_config = config_manager.get_store_config(store_id_upper)
    runtime_options = load_runtime_options()
    telegram_config = load_telegram_config()
    
    # 로거 초기화
    log_config = {'level': 'INFO'}
    structured_logger = StructuredLogger(f"test_{store_id.lower()}_store", log_config)
    
    # 텔레그램 알림 서비스 초기화
    notification_service = None
    if telegram_config:
        notification_service = TelegramAdapter(telegram_config, structured_logger)
    
    # Playwright 설정
    playwright_config = {
        'headless': runtime_options.headless,
        'timeout': runtime_options.timeout,
        'viewport': {
            'width': runtime_options.viewport_width,
            'height': runtime_options.viewport_height
        }
    }
    
    # 매장별 어댑터 생성
    if store_id_upper == 'D':
        return DStoreAdapter(
            store_config=store_config,
            playwright_config=playwright_config,
            structured_logger=structured_logger,
            notification_service=notification_service
        )
    elif store_id_upper == 'A':
        return AStoreAdapter(
            store_config=store_config,
            playwright_config=playwright_config,
            structured_logger=structured_logger,
            notification_service=notification_service
        )
    elif store_id_upper == 'B':
        return BStoreAdapter(
            store_config=store_config,
            playwright_config=playwright_config,
            structured_logger=structured_logger,
            notification_service=notification_service
        )
    elif store_id_upper == 'C':
        return CStoreAdapter(
            store_config=store_config,
            playwright_config=playwright_config,
            structured_logger=structured_logger,
            notification_service=notification_service
        )
    elif store_id_upper == 'E':
        return EStoreAdapter(
            store_config=store_config,
            playwright_config=playwright_config,
            structured_logger=structured_logger,
            notification_service=notification_service
        )
    else:
        raise ValueError(f"지원하지 않는 매장 ID입니다: {store_id}")


# 레지스트리
STORE_REGISTRY: Dict[str, Type[StoreAdapter]] = {
    'D': DStoreAdapter,
    'A': AStoreAdapter,
    'B': BStoreAdapter,
    'C': CStoreAdapter,
    'E': EStoreAdapter
}


def get_supported_stores() -> list:
    """지원하는 매장 목록 반환"""
    return list(STORE_REGISTRY.keys())