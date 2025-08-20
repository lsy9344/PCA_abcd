"""
환경 변수 관리 유틸리티
"""
import os
from typing import Dict, Any
from dotenv import load_dotenv

def load_environment_config() -> Dict[str, Any]:
    """
    환경 설정을 로드합니다.
    로컬 환경에서는 config/environment.local 파일을,
    프로덕션에서는 환경 변수를 사용합니다.
    """
    
    # 환경 확인
    environment = os.getenv('ENVIRONMENT', 'local')
    
    if environment == 'local':
        # 로컬 환경 설정 파일 로드
        env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'environment.local')
        if os.path.exists(env_file):
            load_dotenv(env_file)
        
    # 환경 변수에서 설정값 읽기
    config = {
        # 기본 설정
        'ENVIRONMENT': os.getenv('ENVIRONMENT', 'local'),
        'DEBUG': os.getenv('DEBUG', 'false').lower() == 'true',
        
        # 서버 설정
        'LOCAL_SERVER_HOST': os.getenv('LOCAL_SERVER_HOST', 'localhost'),
        'LOCAL_SERVER_PORT': int(os.getenv('LOCAL_SERVER_PORT', '5000')),
        
        # AWS 설정
        'AWS_REGION': os.getenv('AWS_REGION', 'ap-northeast-2'),
        'AWS_LAMBDA_FUNCTION_NAME': os.getenv('AWS_LAMBDA_FUNCTION_NAME', 'parking-coupon-automation'),
        
        # 매장 A 설정
        'STORE_A': {
            'URL': os.getenv('STORE_A_URL', ''),
            'USERNAME': os.getenv('STORE_A_USERNAME', ''),
            'PASSWORD': os.getenv('STORE_A_PASSWORD', ''),
        },
        
        # 매장 B 설정
        'STORE_B': {
            'URL': os.getenv('STORE_B_URL', ''),
            'USERNAME': os.getenv('STORE_B_USERNAME', ''),
            'PASSWORD': os.getenv('STORE_B_PASSWORD', ''),
        },
        
        # 텔레그램 설정
        'TELEGRAM': {
            'BOT_TOKEN': os.getenv('TELEGRAM_BOT_TOKEN', ''),
            'CHAT_ID': os.getenv('TELEGRAM_CHAT_ID', ''),
        },
        
        # Playwright 설정
        'PLAYWRIGHT': {
            'HEADLESS': os.getenv('PLAYWRIGHT_HEADLESS', 'true').lower() == 'true',
            'TIMEOUT': int(os.getenv('PLAYWRIGHT_TIMEOUT', '30000')),
        },
        
        # 로깅 설정
        'LOGGING': {
            'LEVEL': os.getenv('LOG_LEVEL', 'INFO'),
        }
    }
    
    return config

def get_pc_ip_address():
    """
    현재 PC의 IP 주소를 가져옵니다 (윈도우 환경)
    """
    import subprocess
    import re
    
    try:
        # ipconfig 명령어 실행
        result = subprocess.run(['ipconfig'], capture_output=True, text=True, encoding='cp949')
        
        # IPv4 주소 찾기
        ipv4_pattern = r'IPv4.*?(\d+\.\d+\.\d+\.\d+)'
        matches = re.findall(ipv4_pattern, result.stdout)
        
        # localhost가 아닌 첫 번째 IP 반환
        for ip in matches:
            if not ip.startswith('127.'):
                return ip
                
        return 'localhost'
        
    except Exception as e:
        return 'localhost'

def print_environment_info(config: Dict[str, Any]):
    """현재 환경 설정 정보를 출력합니다. (관리용 함수)"""
    pass

if __name__ == '__main__':
    config = load_environment_config() 