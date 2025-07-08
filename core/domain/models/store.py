"""
매장 도메인 모델
"""
from dataclasses import dataclass
from typing import Dict, Any
from enum import Enum


class StoreType(Enum):
    """매장 타입"""
    A = "A"
    B = "B"


@dataclass
class StoreConfig:
    """매장 설정"""
    store_id: str
    name: str
    website_url: str
    login_username: str
    login_password: str
    discount_types: Dict[str, str]  # 쿠폰 타입 매핑
    max_weekday_coupons: int
    max_weekend_coupons: int
    selectors: Dict[str, Any] = None
    
    def get_coupon_name(self, coupon_key: str) -> str:
        """쿠폰 키로 실제 쿠폰명 조회"""
        return self.discount_types.get(coupon_key, "")
    
    def get_coupon_key(self, coupon_name: str) -> str:
        """쿠폰명으로 키 조회"""
        for key, name in self.discount_types.items():
            if name == coupon_name:
                return key
        return ""


@dataclass
class Store:
    """매장 엔티티"""
    id: str
    name: str
    store_type: StoreType
    config: StoreConfig
    
    def is_type(self, store_type: StoreType) -> bool:
        """매장 타입 확인"""
        return self.store_type == store_type 