#!/usr/bin/env python3
"""
C 매장 테스트 실행용 편의 스크립트
더블클릭하거나 'python run_test.py'로 실행 가능
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    print("🚀 C 매장 테스트 시작...")
    
    # 현재 디렉토리 확인
    current_dir = Path.cwd()
    venv_path = current_dir / "venv"
    test_file = current_dir / "test_c_store_ui.py"
    
    # 가상환경 존재 확인
    if not venv_path.exists():
        print("❌ 가상환경을 찾을 수 없습니다. 먼저 가상환경을 생성하세요.")
        return
    
    # 테스트 파일 존재 확인
    if not test_file.exists():
        print("❌ test_c_store_ui.py 파일을 찾을 수 없습니다.")
        return
    
    print("📍 가상환경에서 테스트 실행 중...")
    
    # macOS/Linux용 가상환경 Python 경로
    if os.name == 'posix':
        python_path = venv_path / "bin" / "python"
    else:  # Windows
        python_path = venv_path / "Scripts" / "python.exe"
    
    try:
        # 가상환경의 Python으로 테스트 실행
        result = subprocess.run([str(python_path), str(test_file)], 
                              capture_output=False, 
                              text=True)
        
        if result.returncode == 0:
            print("✅ 테스트 완료!")
        else:
            print(f"❌ 테스트 실행 중 오류 발생 (코드: {result.returncode})")
            
    except Exception as e:
        print(f"❌ 실행 중 오류: {e}")

if __name__ == "__main__":
    main()
    
    # 사용자가 결과를 볼 수 있도록 잠시 대기 (선택적)
    input("\n계속하려면 Enter를 누르세요...")
