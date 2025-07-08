"""
차량 도메인 모델
"""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime
import re


@dataclass
class Vehicle:
    """차량 엔티티"""
    number: str
    store_id: Optional[str] = None
    searched_at: Optional[datetime] = None
    
    def __post_init__(self):
        """차량번호 유효성 검증"""
        if not self.is_valid_number():
            raise ValueError(f"유효하지 않은 차량번호입니다: {self.number}")
    
    def is_valid_number(self) -> bool:
        """차량번호 유효성 검증"""
        if not self.number:
            return False
        
        # 한국 차량번호 패턴 또는 뒤 4자리만 입력된 경우
        # 예: 12가3456, 123가4567, 5119 (뒤 4자리만)
        full_pattern = r'^\d{2,3}[가-힣]\d{4}$'  # 전체 차량번호
        last_four_pattern = r'^\d{4}$'  # 뒤 4자리만
        
        return bool(re.match(full_pattern, self.number)) or bool(re.match(last_four_pattern, self.number))
    
    def mark_as_searched(self, store_id: str) -> None:
        """검색 완료 표시"""
        self.store_id = store_id
        self.searched_at = datetime.now() 