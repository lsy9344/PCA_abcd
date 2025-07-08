"""
자동화 관련 커스텀 예외
"""


class AutomationException(Exception):
    """자동화 기본 예외"""
    pass


class LoginFailedException(AutomationException):
    """로그인 실패 예외"""
    pass


class VehicleSearchException(AutomationException):
    """차량 검색 예외"""
    pass


class VehicleNotFoundException(VehicleSearchException):
    """차량을 찾을 수 없음 예외"""
    pass


class CouponHistoryException(AutomationException):
    """쿠폰 이력 조회 예외"""
    pass


class CouponApplicationException(AutomationException):
    """쿠폰 적용 예외"""
    pass


class ConfigurationException(AutomationException):
    """설정 관련 예외"""
    pass


class StoreNotSupportedException(AutomationException):
    """지원하지 않는 매장 예외"""
    pass 