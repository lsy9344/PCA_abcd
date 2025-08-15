"""
매장 라우터 - store_id에 따라 적절한 매장 크롤러 클래스를 반환
클린 아키텍처 기반으로 현재 프로젝트 구조에 맞게 구현
"""
from typing import Type, Dict, Any
from infrastructure.web_automation.store_crawlers.a_store_crawler import AStoreCrawler
from infrastructure.web_automation.store_crawlers.b_store_crawler import BStoreCrawler
from infrastructure.web_automation.store_crawlers.c_store_crawler import CStoreCrawler
from infrastructure.web_automation.store_crawlers.d_store_crawler import DStoreCrawler

# 매장 ID와 크롤러 클래스 매핑
STORE_CRAWLER_CLASSES = {
    "A": AStoreCrawler,
    "B": BStoreCrawler,
    "C": CStoreCrawler,
    "D": DStoreCrawler,
}

# 매장별 Lambda 핸들러 파일 매핑
STORE_LAMBDA_FILES = {
    "A": "lambda_a.py",
    "B": "lambda_b.py", 
    "C": "lambda_c.py",
    "D": "lambda_d.py",
}

def get_store_crawler_class(store_id: str) -> Type:
    """
    store_id에 해당하는 매장 크롤러 클래스를 반환
    
    Args:
        store_id (str): 매장 식별자 (A, B, C, D)
        
    Returns:
        Type: 매장 크롤러 클래스
        
    Raises:
        ValueError: 지원하지 않는 store_id인 경우
    """
    crawler_class = STORE_CRAWLER_CLASSES.get(store_id)
    if not crawler_class:
        supported_stores = list(STORE_CRAWLER_CLASSES.keys())
        raise ValueError(f"Unsupported store_id: {store_id}. Supported stores: {supported_stores}")
    return crawler_class

def get_supported_stores() -> list[str]:
    """지원되는 매장 ID 목록 반환"""
    return list(STORE_CRAWLER_CLASSES.keys())

def is_store_supported(store_id: str) -> bool:
    """매장 ID가 지원되는지 확인"""
    return store_id in STORE_CRAWLER_CLASSES

def get_lambda_file_for_store(store_id: str) -> str:
    """매장별 Lambda 핸들러 파일명 반환"""
    lambda_file = STORE_LAMBDA_FILES.get(store_id)
    if not lambda_file:
        raise ValueError(f"No Lambda file configured for store_id: {store_id}")
    return lambda_file

def get_store_info() -> Dict[str, Dict[str, Any]]:
    """모든 매장 정보 반환"""
    return {
        store_id: {
            "crawler_class": crawler_class.__name__,
            "lambda_file": STORE_LAMBDA_FILES.get(store_id, "Not configured"),
            "supported": True
        }
        for store_id, crawler_class in STORE_CRAWLER_CLASSES.items()
    } 