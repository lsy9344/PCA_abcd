"""
설정 관리자
"""
import yaml
import os
from typing import Dict, Any
from pathlib import Path

from core.domain.models.store import StoreConfig
from core.domain.models.discount_policy import DiscountPolicy, CouponRule
from core.domain.models.coupon import CouponType


class ConfigManager:
    """설정 관리자"""
    
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            config_dir = Path(__file__).parent
        
        self.config_dir = Path(config_dir)
        self.base_config = self._load_base_config()
        self._store_configs = {}
    
    def _load_base_config(self) -> Dict[str, Any]:
        """기본 설정 로드"""
        base_config_path = self.config_dir / "base_config.yaml"
        with open(base_config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def get_store_config(self, store_id: str) -> StoreConfig:
        """매장 설정 조회"""
        if store_id not in self._store_configs:
            self._store_configs[store_id] = self._load_store_config(store_id)
        return self._store_configs[store_id]
    
    def _load_store_config(self, store_id: str) -> StoreConfig:
        """매장별 설정 로드"""
        config_path = self.config_dir / "store_configs" / f"{store_id.lower()}_store_config.yaml"
        
        if not config_path.exists():
            raise FileNotFoundError(f"매장 설정 파일을 찾을 수 없습니다: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        # 쿠폰 타입 매핑 생성
        discount_types = {}
        for key, coupon_info in config_data['coupons'].items():
            discount_types[key] = coupon_info['name']
        
        return StoreConfig(
            store_id=config_data['store']['id'],
            name=config_data['store']['name'],
            website_url=config_data['store']['website_url'],
            login_username=config_data['login']['username'],
            login_password=config_data['login']['password'],
            discount_types=discount_types,
            max_weekday_coupons=config_data['discount_policy']['weekday']['max_coupons'],
            max_weekend_coupons=config_data['discount_policy']['weekend']['max_coupons'],
            selectors=config_data.get('selectors', {})
        )
    
    def get_discount_policy(self, store_id: str) -> DiscountPolicy:
        """할인 정책 조회"""
        config_path = self.config_dir / "store_configs" / f"{store_id.lower()}_store_config.yaml"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        policy_data = config_data['discount_policy']
        
        return DiscountPolicy(
            store_id=store_id,
            weekday_target_hours=policy_data['weekday']['target_hours'],
            weekend_target_hours=policy_data['weekend']['target_hours'],
            weekday_max_coupons=policy_data['weekday']['max_coupons'],
            weekend_max_coupons=policy_data['weekend']['max_coupons']
        )
    
    def get_coupon_rules(self, store_id: str) -> list[CouponRule]:
        """쿠폰 규칙 조회"""
        config_path = self.config_dir / "store_configs" / f"{store_id.lower()}_store_config.yaml"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        rules = []
        for key, coupon_info in config_data['coupons'].items():
            coupon_type = CouponType(coupon_info['type'])
            
            rules.append(CouponRule(
                coupon_key=key,
                coupon_name=coupon_info['name'],
                coupon_type=coupon_type,
                duration_minutes=coupon_info['duration_minutes'],
                priority=coupon_info.get('priority', 0)
            ))
        
        return rules
    
    def get_playwright_config(self) -> Dict[str, Any]:
        """Playwright 설정 조회"""
        return self.base_config['playwright']
    
    def get_telegram_config(self) -> Dict[str, Any]:
        """텔레그램 설정 조회"""
        return self.base_config['telegram']
    
    def get_logging_config(self) -> Dict[str, Any]:
        """로깅 설정 조회"""
        return self.base_config['logging'] 