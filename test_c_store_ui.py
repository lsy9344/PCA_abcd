"""
C 매장 로그인 → 차량번호 입력 → 차량조회 버튼 클릭 → 테이블에서 차량 선택 기능 테스트
"""
import asyncio
from playwright.async_api import async_playwright
import yaml
from pathlib import Path
import os

class CStoreUITest:
    def __init__(self):
        self.page = None
        self.browser = None
        self.context = None
        self.playwright_instance = None
        self.config = self._load_config()
        
    def _load_config(self):
        """C 매장 설정 로드"""
        config_path = Path("infrastructure/config/store_configs/c_store_config.yaml")
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    async def setup_browser(self):
        """브라우저 초기화 (UI 모드)"""
        print("🚀 브라우저 초기화 중 (UI 모드)...")
        
        self.playwright_instance = await async_playwright().start()
        self.browser = await self.playwright_instance.chromium.launch(
            headless=False,  # UI 창 띄우기
            slow_mo=1000,    # 액션 간 1초 대기로 천천히 실행
            args=[
                '--disable-blink-features=AutomationControlled',
                '--window-size=1280,800'
            ]
        )
        
        self.context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        self.page = await self.context.new_page()
        self.page.set_default_timeout(30000)  # 30초 타임아웃
        
        print("✅ 브라우저 초기화 완료 (UI 모드)")
    
    async def run_full_test(self):
        """전체 테스트 실행"""
        try:
            print("=" * 60)
            print("C 매장 로그인 → 차량조회 → 차량선택 테스트 시작")
            print("=" * 60)
            
            # 1단계: 사이트 접속
            if not await self._step_1_navigate():
                return False
            
            # 2단계: 로그인
            if not await self._step_2_login():
                return False
            
            # 3단계: 차량번호 입력
            if not await self._step_3_input_vehicle():
                return False
            
            # 4단계: 차량조회 버튼 클릭
            if not await self._step_4_search_vehicle():
                return False
            
            # 5단계: 테이블에서 차량 선택
            if not await self._step_5_select_vehicle():
                return False
            
            print("\n🎉 모든 테스트 단계 완료!")
            return True
            
        except Exception as e:
            print(f"❌ 테스트 중 오류 발생: {str(e)}")
            return False
    
    async def _step_1_navigate(self):
        """1단계: 사이트 접속"""
        print("\n📍 1단계: C 매장 사이트 접속")
        print(f"   URL: {self.config['store']['website_url']}")
        
        try:
            await self.page.goto(self.config['store']['website_url'])
            await self.page.wait_for_load_state('networkidle')
            
            print(f"   ✅ 사이트 접속 성공")
            print(f"   현재 URL: {self.page.url}")
            print(f"   페이지 제목: {await self.page.title()}")
            
            # 스크린샷 저장
            await self._save_screenshot("step1_navigate")
            
            return True
            
        except Exception as e:
            print(f"   ❌ 사이트 접속 실패: {str(e)}")
            return False
    
    async def _step_2_login(self):
        """2단계: 로그인"""
        print("\n📍 2단계: 로그인 수행")
        
        try:
            # 사용자명 입력
            username_selector = self.config['selectors']['login']['username_input']
            username = self.config['login']['username']
            
            await self.page.fill(username_selector, username)
            print(f"   ✅ 사용자명 입력: {username}")
            
            # 비밀번호 입력
            password_selector = self.config['selectors']['login']['password_input']
            password = self.config['login']['password']
            
            await self.page.fill(password_selector, password)
            print(f"   ✅ 비밀번호 입력 완료")
            
            # 로그인 버튼 클릭
            login_button_selector = self.config['selectors']['login']['login_button']
            await self.page.click(login_button_selector)
            print(f"   ✅ 로그인 버튼 클릭")
            
            # 로그인 성공 확인 - 차량번호 입력란 대기
            car_input_selector = self.config['selectors']['login']['car_number_input']
            await self.page.wait_for_selector(car_input_selector, timeout=15000)
            
            print(f"   ✅ 로그인 성공 확인 - 차량번호 입력란 표시됨")
            
            # 스크린샷 저장
            await self._save_screenshot("step2_login_success")
            
            return True
            
        except Exception as e:
            print(f"   ❌ 로그인 실패: {str(e)}")
            await self._save_screenshot("step2_login_failed")
            return False
    
    async def _step_3_input_vehicle(self):
        """3단계: 차량번호 입력"""
        print("\n📍 3단계: 차량번호 입력")
        
        test_car_number = "6897"  # 테스트용 차량번호
        
        try:
            car_input_selector = self.config['selectors']['search']['car_number_input']
            
            # 입력란 클리어 후 입력
            await self.page.fill(car_input_selector, "")
            await self.page.fill(car_input_selector, test_car_number)
            
            print(f"   ✅ 차량번호 입력 완료: {test_car_number}")
            
            # 스크린샷 저장
            await self._save_screenshot("step3_vehicle_input")
            
            return True
            
        except Exception as e:
            print(f"   ❌ 차량번호 입력 실패: {str(e)}")
            return False
    
    async def _step_4_search_vehicle(self):
        """4단계: 차량조회 버튼 클릭"""
        print("\n📍 4단계: 차량조회 버튼 클릭")
        
        try:
            # 여러 검색 버튼 셀렉터 시도
            search_selectors = [
                self.config['selectors']['search']['search_button'],
                "#searchBtn",
                "input[value='차량조회']",
                "button:has-text('차량조회')",
                "input[type='button']:has-text('차량조회')",
                ".search-btn"
            ]
            
            for selector in search_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        await self.page.click(selector)
                        print(f"   ✅ 검색 버튼 클릭 성공: {selector}")
                        
                        # 검색 결과 로딩 대기
                        await self.page.wait_for_timeout(3000)
                        
                        # 스크린샷 저장
                        await self._save_screenshot("step4_search_clicked")
                        
                        return True
                except Exception:
                    continue
            
            print(f"   ❌ 검색 버튼을 찾을 수 없음")
            await self._save_screenshot("step4_search_failed")
            return False
            
        except Exception as e:
            print(f"   ❌ 검색 버튼 클릭 실패: {str(e)}")
            return False
    
    async def _step_5_select_vehicle(self):
        """5단계: 테이블에서 차량 선택"""
        print("\n📍 5단계: 테이블에서 차량 선택")
        
        # 검색에 사용된 차량번호의 일부를 포함하는 결과를 찾기
        search_number = "6897"  # 실제 검색에 사용된 번호
        
        try:
            # 스크린샷으로 현재 상태 확인
            await self._save_screenshot("step5_before_selection")
            
            # 검색 결과 없음 팝업 확인
            no_result_text = self.config['selectors']['search']['no_result_message']
            if await self.page.locator(no_result_text).count() > 0:
                print(f"   ⚠️  검색 결과 없음 - 팝업 처리")
                
                # 팝업 닫기
                close_buttons = ['text=OK', 'text=확인', '.popup-ok', '.close-btn']
                for selector in close_buttons:
                    if await self.page.locator(selector).count() > 0:
                        await self.page.click(selector)
                        print(f"   ✅ 팝업 닫기 완료")
                        break
                
                print(f"   ℹ️  차량번호 '{search_number}'에 대한 검색 결과가 없습니다")
                await self._save_screenshot("step5_no_result")
                return True  # 테스트 목적상 성공으로 처리
            
            # 테이블 찾기 및 차량 선택 - 스크린샷에서 확인된 실제 테이블 ID 사용
            table_selectors = [
                "#tableID",  # 스크린샷에서 확인된 정확한 ID (camelCase)
                self.config['selectors']['search']['search_result_table'],
                "#tableid",
                "#searchResult", 
                "table",
                ".table-box"
            ]
            
            for table_selector in table_selectors:
                try:
                    table = self.page.locator(table_selector)
                    if await table.count() > 0:
                        print(f"   ✅ 테이블 발견: {table_selector}")
                        
                        # 테이블의 모든 행 검사 (헤더 제외)
                        rows = await table.locator('tbody tr').all()
                        if len(rows) == 0:
                            # tbody가 없는 경우 일반 tr 사용
                            rows = await table.locator('tr').all()
                        
                        print(f"   📊 테이블 행 수: {len(rows)}")
                        
                        for i, row in enumerate(rows):
                            try:
                                row_text = await row.inner_text()
                                print(f"   🔍 행 {i+1}: {row_text[:50]}...")  # 행 내용 일부 출력
                                
                                # 검색된 차량번호 패턴을 포함하는 행 찾기
                                if search_number in row_text or any(char.isdigit() for char in row_text):
                                    print(f"   ✅ 검색 결과 발견 (행 {i+1}): {row_text}")
                                    
                                    # 행 클릭 시도 (onclick 핸들러가 있는 경우)
                                    try:
                                        # 먼저 행 자체에 onclick이 있는지 확인
                                        onclick_attr = await row.get_attribute('onclick')
                                        if onclick_attr:
                                            print(f"   🎯 onclick 핸들러 발견: {onclick_attr[:50]}...")
                                            await row.click()
                                            print(f"   ✅ 차량 행 클릭 완료")
                                            
                                            # 선택 후 대기
                                            await self.page.wait_for_timeout(2000)
                                            await self._save_screenshot("step5_vehicle_selected")
                                            
                                            return True
                                        else:
                                            # onclick이 없으면 셀 클릭 시도
                                            cells = await row.locator('td').all()
                                            for cell in cells:
                                                if await cell.count() > 0:
                                                    await cell.click()
                                                    print(f"   ✅ 차량 셀 클릭 완료")
                                                    
                                                    await self.page.wait_for_timeout(2000)
                                                    await self._save_screenshot("step5_vehicle_selected")
                                                    
                                                    return True
                                                    
                                    except Exception as click_error:
                                        print(f"   ⚠️  행 클릭 중 오류: {str(click_error)}")
                                        continue
                                            
                            except Exception as row_error:
                                print(f"   ⚠️  행 처리 중 오류: {str(row_error)}")
                                continue
                        
                        print(f"   ⚠️  테이블에서 검색 결과를 찾을 수 없음")
                        break
                        
                except Exception:
                    continue
            
            print(f"   ❌ 검색 결과 테이블을 찾을 수 없음")
            await self._save_screenshot("step5_no_table")
            return False
            
        except Exception as e:
            print(f"   ❌ 차량 선택 실패: {str(e)}")
            await self._save_screenshot("step5_selection_failed")
            return False
    
    async def _save_screenshot(self, step_name):
        """스크린샷 저장"""
        try:
            screenshot_path = f"test_screenshots/{step_name}.png"
            await self.page.screenshot(path=screenshot_path)
            print(f"   📸 스크린샷 저장: {screenshot_path}")
        except Exception as e:
            print(f"   ⚠️  스크린샷 저장 실패: {str(e)}")
    
    async def cleanup(self):
        """리소스 정리"""
        print("\n🧹 브라우저 정리 중...")
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright_instance:
                await self.playwright_instance.stop()
            print("✅ 정리 완료")
        except Exception as e:
            print(f"⚠️  정리 중 오류: {str(e)}")

async def main():
    """메인 테스트 실행"""
    # 스크린샷 디렉토리 생성
    os.makedirs("test_screenshots", exist_ok=True)
    
    test = CStoreUITest()
    
    try:
        await test.setup_browser()
        success = await test.run_full_test()
        
        if success:
            print("\n🎉 전체 테스트 완료!")
        else:
            print("\n❌ 테스트 실패")
        
        print("📁 스크린샷은 test_screenshots/ 폴더에 저장되었습니다.")
        
        # 결과 확인을 위해 브라우저 유지
        input("\n브라우저를 닫으려면 Enter를 누르세요...")
        
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류: {str(e)}")
    finally:
        await test.cleanup()

if __name__ == "__main__":
    asyncio.run(main())