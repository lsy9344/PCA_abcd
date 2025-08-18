"""공용 설정 로더"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class StoreConfig:
    """매장 설정"""
    store_id: str
    website_url: str
    login_username: str
    login_password: str
    selectors: Dict[str, Any]
    coupons: Dict[str, Any]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], store_id: str) -> 'StoreConfig':
        """딕셔너리에서 StoreConfig 생성"""
        return cls(
            store_id=store_id,
            website_url=data['store']['website_url'],
            login_username=data['login']['username'],
            login_password=data['login']['password'],
            selectors=data.get('selectors', {}),
            coupons=data.get('coupons', {})
        )


@dataclass
class RuntimeOptions:
    """런타임 옵션"""
    headless: bool = True
    timeout: int = 30000
    viewport_width: int = 1280
    viewport_height: int = 800
    timezone: str = 'Asia/Seoul'
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RuntimeOptions':
        """딕셔너리에서 RuntimeOptions 생성"""
        return cls(
            headless=data.get('headless', True),
            timeout=data.get('timeout', 30000),
            viewport_width=data.get('viewport', {}).get('width', 1280),
            viewport_height=data.get('viewport', {}).get('height', 800),
            timezone=data.get('timezone', 'Asia/Seoul')
        )


def load_store_config(store_id: str) -> StoreConfig:
    """매장별 설정 로드"""
    config_path = Path(f"infrastructure/config/store_configs/{store_id.lower()}_store_config.yaml")
    
    if not config_path.exists():
        raise FileNotFoundError(f"매장 설정 파일을 찾을 수 없습니다: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)
    
    return StoreConfig.from_dict(config_data, store_id.upper())


def load_runtime_options() -> RuntimeOptions:
    """런타임 옵션 로드"""
    base_config_path = Path("infrastructure/config/base_config.yaml")
    
    if not base_config_path.exists():
        # 기본값 반환
        return RuntimeOptions()
    
    with open(base_config_path, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)
    
    runtime_data = config_data.get('runtime', {})
    return RuntimeOptions.from_dict(runtime_data)


def load_telegram_config() -> Optional[Dict[str, Any]]:
    """텔레그램 설정 로드"""
    base_config_path = Path("infrastructure/config/base_config.yaml")
    
    if not base_config_path.exists():
        return None
    
    with open(base_config_path, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)
    
    return config_data.get('telegram')