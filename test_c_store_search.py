"""
C 매장 차량 검색 및 선택 기능 테스트
스크린샷을 기반으로 실제 동작 검증
"""
import asyncio
from playwright.async_api import async_playwright
import yaml
import os
from pathlib import Path

class CStoreSearchTester:
    def __init__(self):
        self.page = None
        self.browser = None
        self.context = None
        self.config = self._load_config()
        
    def _load_config(self):
        """C 매장 설정 로드"""
        config_path = Path("infrastructure/config/store_configs/c_store_config.yaml")
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    async def setup_browser(self):
        """브라우저 초기화"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=False,  # UI 확인을 위해 headless=False
            args=['--disable-blink-features=AutomationControlled']
        )
        self.context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        self.page = await self.context.new_page()
        
    async def test_login_and_search_flow(self, test_car_number="27라1234"):
        """로그인부터 차량 검색 및 선택까지 전체 플로우 테스트"""
        try:
            print("=== C 매장 차량 검색 테스트 시작 ===")
            
            # 1. 사이트 접속
            print(f"1. 사이트 접속: {self.config['store']['website_url']}")
            await self.page.goto(self.config['store']['website_url'])
            await self.page.wait_for_load_state('networkidle')
            
            # 2. 로그인
            print("2. 로그인 진행")
            await self._perform_login()
            
            # 3. 차량번호 입력 및 검색
            print(f"3. 차량번호 입력 및 검색: {test_car_number}")
            await self._perform_vehicle_search(test_car_number)
            
            # 4. 검색 결과 테이블 확인 및 차량 선택
            print("4. 검색 결과 테이블에서 차량 선택")
            selected = await self._select_vehicle_from_table(test_car_number)
            
            if selected:
                print("✅ 전체 플로우 테스트 성공!")
                return True
            else:
                print("❌ 차량 선택 실패")
                return False
                
        except Exception as e:
            print(f"❌ 테스트 중 오류 발생: {str(e)}")
            return False
    
    async def _perform_login(self):
        """로그인 수행"""
        try:
            # 로그인 폼 입력
            username_input = self.config['selectors']['login']['username_input']
            password_input = self.config['selectors']['login']['password_input']
            login_button = self.config['selectors']['login']['login_button']
            
            await self.page.fill(username_input, self.config['login']['username'])
            await self.page.fill(password_input, self.config['login']['password'])
            await self.page.click(login_button)
            
            # 로그인 후 차량번호 입력란 대기
            car_input = self.config['selectors']['login']['car_number_input']
            await self.page.wait_for_selector(car_input, timeout=15000)
            
            # 팝업 처리
            await self._handle_popups()
            print("✅ 로그인 성공")
            
        except Exception as e:
            print(f"❌ 로그인 실패: {str(e)}")
            raise
    
    async def _perform_vehicle_search(self, car_number):
        """차량 검색 수행"""
        try:
            # 차량번호 입력
            car_input_selector = self.config['selectors']['search']['car_number_input']
            await self.page.fill(car_input_selector, car_number)
            print(f"   - 차량번호 입력 완료: {car_number}")
            
            # 검색 버튼 클릭 (여러 가능한 셀렉터 시도)
            search_selectors = [
                self.config['selectors']['search']['search_button'],
                "#searchBtn",
                "input[value='차량조회']",
                "button:has-text('차량조회')",
                "input[type='button']:has-text('차량조회')"
            ]
            
            search_clicked = False
            for selector in search_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        await self.page.click(selector)
                        print(f"   - 검색 버튼 클릭 완료: {selector}")
                        search_clicked = True
                        break
                except:
                    continue
            
            if not search_clicked:
                raise Exception("검색 버튼을 찾을 수 없음")
            
            # 검색 결과 로딩 대기
            await self.page.wait_for_timeout(3000)
            print("   - 검색 결과 로딩 대기 완료")
            
        except Exception as e:
            print(f"❌ 차량 검색 실패: {str(e)}")
            raise
    
    async def _select_vehicle_from_table(self, car_number):
        """검색 결과 테이블에서 차량 선택"""
        try:
            # 스크린샷 기반으로 테이블 셀렉터들 확인
            table_selectors = [
                "#tableid",  # 스크린샷에서 확인된 테이블 ID
                "#searchResult",  # 설정파일의 테이블 셀렉터
                "table",
                ".table-box"
            ]
            
            table_found = False
            for table_selector in table_selectors:
                try:
                    table = self.page.locator(table_selector)
                    if await table.count() > 0:
                        print(f"   - 테이블 발견: {table_selector}")
                        
                        # 테이블 내용 출력 (디버깅용)
                        table_html = await table.inner_html()
                        print(f"   - 테이블 HTML 일부: {table_html[:200]}...")
                        
                        # 차량번호가 포함된 행 찾기
                        rows = await table.locator('tr').all()
                        print(f"   - 총 {len(rows)}개 행 발견")
                        
                        for i, row in enumerate(rows):
                            try:
                                row_text = await row.inner_text()
                                print(f"   - 행 {i}: {row_text[:100]}...")
                                
                                if car_number in row_text:
                                    # 차량번호가 포함된 행에서 클릭 가능한 요소 찾기
                                    clickable_elements = [
                                        row.locator('td:has-text("' + car_number + '")'),
                                        row.locator('a'),
                                        row.locator('[onclick]'),
                                        row.locator('td').first
                                    ]
                                    
                                    for element in clickable_elements:
                                        if await element.count() > 0:
                                            await element.first.click()
                                            print(f"✅ 차량번호 '{car_number}' 클릭 완료")
                                            await self.page.wait_for_timeout(2000)
                                            return True
                                            
                            except Exception as row_error:
                                print(f"   - 행 {i} 처리 중 오류: {str(row_error)}")
                                continue
                        
                        table_found = True
                        break
                        
                except Exception as selector_error:
                    print(f"   - 셀렉터 {table_selector} 시도 중 오류: {str(selector_error)}")
                    continue
            
            if not table_found:
                print("❌ 검색 결과 테이블을 찾을 수 없음")
                # 현재 페이지 상태 출력
                await self._debug_page_state()
                
            return False
            
        except Exception as e:
            print(f"❌ 차량 선택 실패: {str(e)}")
            return False
    
    async def _debug_page_state(self):
        """디버깅을 위한 페이지 상태 출력"""
        try:
            print("=== 페이지 디버깅 정보 ===")
            print(f"현재 URL: {self.page.url}")
            
            # 페이지의 모든 테이블 요소 확인
            tables = await self.page.locator('table').all()
            print(f"페이지의 테이블 개수: {len(tables)}")
            
            for i, table in enumerate(tables):
                table_html = await table.inner_html()
                print(f"테이블 {i}: {table_html[:300]}...")
            
            # ID가 있는 요소들 확인
            elements_with_id = await self.page.evaluate("""
                () => {
                    const elements = document.querySelectorAll('[id]');
                    return Array.from(elements).map(el => el.id);
                }
            """)
            print(f"ID가 있는 요소들: {elements_with_id}")
            
        except Exception as e:
            print(f"디버깅 정보 수집 실패: {str(e)}")
    
    async def _handle_popups(self):
        """팝업 처리"""
        try:
            popup_selectors = [
                self.config['selectors']['popups']['ok_button'],
                self.config['selectors']['popups']['close_button'],
                'text=확인', 'text=OK', 'text=닫기'
            ]
            
            for selector in popup_selectors:
                try:
                    popup_button = self.page.locator(selector)
                    if await popup_button.count() > 0:
                        await popup_button.first.click()
                        await self.page.wait_for_timeout(1000)
                        print(f"   - 팝업 처리 완료: {selector}")
                        break
                except:
                    continue
                    
        except Exception as e:
            print(f"팝업 처리 실패: {str(e)}")
    
    async def cleanup(self):
        """리소스 정리"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

async def main():
    """메인 테스트 실행"""
    tester = CStoreSearchTester()
    
    try:
        await tester.setup_browser()
        success = await tester.test_login_and_search_flow("27라1234")
        
        if success:
            print("\n🎉 모든 테스트 통과!")
        else:
            print("\n❌ 테스트 실패")
            
        # 결과 확인을 위해 잠시 대기
        input("\n결과 확인 후 Enter를 눌러 종료...")
        
    except Exception as e:
        print(f"테스트 실행 중 오류: {str(e)}")
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())