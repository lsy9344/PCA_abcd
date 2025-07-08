"""
날짜 관련 유틸리티
"""
from datetime import datetime
import holidays


class DateUtils:
    """날짜 유틸리티 클래스"""
    
    # 한국 공휴일 객체
    _korea_holidays = holidays.Korea()
    
    @classmethod
    def is_weekday(cls, date: datetime) -> bool:
        """평일 여부 확인 (월~금, 공휴일 제외)"""
        # 토요일(5), 일요일(6)이면 주말
        if date.weekday() >= 5:
            return False
        
        # 공휴일이면 주말로 처리
        if date.date() in cls._korea_holidays:
            return False
        
        return True
    
    @classmethod
    def is_weekend(cls, date: datetime) -> bool:
        """주말 여부 확인 (토, 일, 공휴일 포함)"""
        return not cls.is_weekday(date)
    
    @classmethod
    def get_day_type_str(cls, date: datetime) -> str:
        """날짜 타입 문자열 반환"""
        return "평일" if cls.is_weekday(date) else "주말" 