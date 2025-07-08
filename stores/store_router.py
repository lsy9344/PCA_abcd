"""
매장 라우터 - store_id에 따라 적절한 매장 클래스를 반환
"""
from typing import Type
from .base_store import BaseStore
from .a_store import AStore
# 매장 클래스 임포트
from core.domain.stores.b_store import BStore

# 매장 ID와 클래스 매핑
STORE_CLASSES = {
    "A": AStore,
    "B": BStore,
}

def get_store_class(store_id: str) -> Type[BaseStore]:
    """
    store_id에 해당하는 매장 클래스를 반환
    
    Args:
        store_id (str): 매장 식별자
        
    Returns:
        Type[BaseStore]: 매장 클래스
        
    Raises:
        ValueError: 지원하지 않는 store_id인 경우
    """
    store_class = STORE_CLASSES.get(store_id)
    if not store_class:
        raise ValueError(f"Unsupported store_id: {store_id}")
    return store_class 