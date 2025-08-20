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
            print(f"로컬 환경 설정 로드: {env_file}")
        else:
            print(f"환경 설정 파일을 찾을 수 없습니다: {env_file}")
    
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
        print(f"IP 주소 조회 실패: {e}")
        return 'localhost'

def print_environment_info(config: Dict[str, Any]):
    """
    현재 환경 설정 정보를 출력합니다.
    """
    print("========================================")
    print("현재 환경 설정:")
    print("========================================")
    print(f"환경: {config['ENVIRONMENT']}")
    print(f"디버그 모드: {config['DEBUG']}")
    print(f"서버 주소: {config['LOCAL_SERVER_HOST']}:{config['LOCAL_SERVER_PORT']}")
    print(f"Playwright 헤드리스: {config['PLAYWRIGHT']['HEADLESS']}")
    print(f"로그 레벨: {config['LOGGING']['LEVEL']}")
    
    # IP 주소 정보
    ip_address = get_pc_ip_address()
    print(f"PC IP 주소: {ip_address}")
    
    # 매장 설정 확인
    store_a_configured = bool(config['STORE_A']['URL'] and config['STORE_A']['USERNAME'])
    store_b_configured = bool(config['STORE_B']['URL'] and config['STORE_B']['USERNAME'])
    print(f"매장 A 설정: {'✓' if store_a_configured else '✗'}")
    print(f"매장 B 설정: {'✓' if store_b_configured else '✗'}")
    
    # 텔레그램 설정 확인
    telegram_configured = bool(config['TELEGRAM']['BOT_TOKEN'] and config['TELEGRAM']['CHAT_ID'])
    print(f"텔레그램 알림: {'✓' if telegram_configured else '✗'}")
    
    print("========================================")
    
    # 웹훅 URL 정보
    webhook_url_local = f"http://localhost:{config['LOCAL_SERVER_PORT']}/webhook"
    webhook_url_network = f"http://{ip_address}:{config['LOCAL_SERVER_PORT']}/webhook"
    
    print("웹훅 URL:")
    print(f"  로컬: {webhook_url_local}")
    print(f"  네트워크: {webhook_url_network}")
    print("========================================")

if __name__ == '__main__':
    # 테스트 실행
    config = load_environment_config()
    print_environment_info(config) 