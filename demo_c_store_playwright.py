"""
C 매장 크롤러 현재 구성 단계 시연
Playwright MCP를 통한 실제 동작 확인
"""
import asyncio
from playwright.async_api import async_playwright
import yaml
from pathlib import Path
import time

class CStoreDemo:
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
        print("🚀 브라우저 초기화 중...")
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
        print("✅ 브라우저 초기화 완료")
    
    async def demonstrate_stages(self):
        """단계별 시연"""
        try:
            print("=== C 매장 크롤러 구성 단계 시연 ===\n")
            
            # 1단계: 사이트 접속
            await self._stage_1_navigation()
            
            # 2단계: 로그인 페이지 분석
            await self._stage_2_login_analysis()
            
            # 3단계: 로그인 시도
            await self._stage_3_login_attempt()
            
            # 4단계: 차량 검색 인터페이스 확인
            await self._stage_4_search_interface()
            
            # 5단계: 차량 검색 시연
            await self._stage_5_vehicle_search()
            
        except Exception as e:
            print(f"❌ 시연 중 오류 발생: {str(e)}")
    
    async def _stage_1_navigation(self):
        """1단계: 사이트 접속"""
        print("📍 1단계: C 매장 사이트 접속")
        print(f"   URL: {self.config['store']['website_url']}")
        
        try:
            await self.page.goto(self.config['store']['website_url'])
            await self.page.wait_for_load_state('networkidle')
            
            current_url = self.page.url
            title = await self.page.title()
            
            print(f"   ✅ 접속 성공")
            print(f"   현재 URL: {current_url}")
            print(f"   페이지 제목: {title}")
            
            # 페이지 스크린샷
            await self.page.screenshot(path="demo_screenshots/stage1_navigation.png")
            print(f"   📸 스크린샷 저장: demo_screenshots/stage1_navigation.png")
            
        except Exception as e:
            print(f"   ❌ 접속 실패: {str(e)}")
        
        await asyncio.sleep(2)
    
    async def _stage_2_login_analysis(self):
        """2단계: 로그인 페이지 분석"""
        print("\n📍 2단계: 로그인 요소 분석")
        
        login_elements = self.config['selectors']['login']
        
        for element_name, selector in login_elements.items():
            try:
                element = self.page.locator(selector)
                count = await element.count()
                
                if count > 0:
                    print(f"   ✅ {element_name}: {selector} (찾음)")
                    
                    # 요소 하이라이트
                    await element.first.highlight()
                    
                else:
                    print(f"   ❌ {element_name}: {selector} (없음)")
                    
            except Exception as e:
                print(f"   ⚠️ {element_name}: {selector} (오류: {str(e)})")
        
        await self.page.screenshot(path="demo_screenshots/stage2_login_analysis.png")
        print(f"   📸 로그인 분석 스크린샷: demo_screenshots/stage2_login_analysis.png")
        
        await asyncio.sleep(3)
    
    async def _stage_3_login_attempt(self):
        """3단계: 로그인 시도"""
        print("\n📍 3단계: 로그인 수행")
        
        try:
            # 사용자명 입력
            username_selector = self.config['selectors']['login']['username_input']
            username = self.config['login']['username']
            
            if await self.page.locator(username_selector).count() > 0:
                await self.page.fill(username_selector, username)
                print(f"   ✅ 사용자명 입력 완료: {username}")
            
            # 비밀번호 입력
            password_selector = self.config['selectors']['login']['password_input']
            password = self.config['login']['password']
            
            if await self.page.locator(password_selector).count() > 0:
                await self.page.fill(password_selector, password)
                print(f"   ✅ 비밀번호 입력 완료")
            
            # 입력 후 스크린샷
            await self.page.screenshot(path="demo_screenshots/stage3_login_filled.png")
            print(f"   📸 로그인 정보 입력 스크린샷: demo_screenshots/stage3_login_filled.png")
            
            # 로그인 버튼 클릭
            login_button_selector = self.config['selectors']['login']['login_button']
            
            if await self.page.locator(login_button_selector).count() > 0:
                await self.page.click(login_button_selector)
                print(f"   ✅ 로그인 버튼 클릭 완료")
                
                # 로그인 후 대기
                await asyncio.sleep(3)
                
                # 로그인 후 상태 확인
                await self._check_login_result()
            
        except Exception as e:
            print(f"   ❌ 로그인 실패: {str(e)}")
    
    async def _check_login_result(self):
        """로그인 결과 확인"""
        print("   🔍 로그인 결과 확인 중...")
        
        try:
            # 차량번호 입력란이 나타나는지 확인
            car_input_selector = self.config['selectors']['login']['car_number_input']
            
            # 15초 대기
            await self.page.wait_for_selector(car_input_selector, timeout=15000)
            print("   ✅ 로그인 성공 - 차량번호 입력란 확인됨")
            
            # 로그인 성공 스크린샷
            await self.page.screenshot(path="demo_screenshots/stage3_login_success.png")
            print(f"   📸 로그인 성공 스크린샷: demo_screenshots/stage3_login_success.png")
            
        except Exception as e:
            print(f"   ❌ 로그인 실패 또는 확인 불가: {str(e)}")
            await self.page.screenshot(path="demo_screenshots/stage3_login_failed.png")
    
    async def _stage_4_search_interface(self):
        """4단계: 차량 검색 인터페이스 확인"""
        print("\n📍 4단계: 차량 검색 인터페이스 분석")
        
        search_elements = self.config['selectors']['search']
        
        for element_name, selector in search_elements.items():
            try:
                element = self.page.locator(selector)
                count = await element.count()
                
                if count > 0:
                    print(f"   ✅ {element_name}: {selector} (찾음)")
                    
                    # 검색 관련 요소 하이라이트
                    if element_name in ['car_number_input', 'search_button']:
                        await element.first.highlight()
                        await asyncio.sleep(1)
                    
                else:
                    print(f"   ❌ {element_name}: {selector} (없음)")
                    
            except Exception as e:
                print(f"   ⚠️ {element_name}: {selector} (오류: {str(e)})")
        
        await self.page.screenshot(path="demo_screenshots/stage4_search_interface.png")
        print(f"   📸 검색 인터페이스 스크린샷: demo_screenshots/stage4_search_interface.png")
        
        await asyncio.sleep(2)
    
    async def _stage_5_vehicle_search(self):
        """5단계: 차량 검색 시연"""
        print("\n📍 5단계: 차량 검색 및 선택 시연")
        
        test_car_number = "27라1234"
        
        try:
            # 차량번호 입력
            car_input_selector = self.config['selectors']['search']['car_number_input']
            
            if await self.page.locator(car_input_selector).count() > 0:
                await self.page.fill(car_input_selector, test_car_number)
                print(f"   ✅ 차량번호 입력: {test_car_number}")
                
                # 입력 후 스크린샷
                await self.page.screenshot(path="demo_screenshots/stage5_car_input.png")
                print(f"   📸 차량번호 입력 스크린샷: demo_screenshots/stage5_car_input.png")
                
                # 검색 버튼 클릭 시도
                await self._attempt_search_click()
                
                # 검색 결과 대기 및 분석
                await self._analyze_search_results(test_car_number)
            
        except Exception as e:
            print(f"   ❌ 차량 검색 시연 실패: {str(e)}")
    
    async def _attempt_search_click(self):
        """검색 버튼 클릭 시도"""
        print("   🔍 검색 버튼 찾는 중...")
        
        search_selectors = [
            self.config['selectors']['search']['search_button'],
            "#searchBtn",
            "input[value='차량조회']",
            "button:has-text('차량조회')",
            "input[type='button']:has-text('차량조회')"
        ]
        
        for selector in search_selectors:
            try:
                if await self.page.locator(selector).count() > 0:
                    await self.page.locator(selector).first.highlight()
                    await asyncio.sleep(1)
                    await self.page.click(selector)
                    print(f"   ✅ 검색 버튼 클릭 성공: {selector}")
                    await asyncio.sleep(3)  # 검색 결과 로딩 대기
                    return
            except Exception:
                continue
        
        print("   ❌ 검색 버튼을 찾을 수 없음")
    
    async def _analyze_search_results(self, car_number):
        """검색 결과 분석"""
        print("   🔍 검색 결과 분석 중...")
        
        # 검색 결과 스크린샷
        await self.page.screenshot(path="demo_screenshots/stage5_search_results.png")
        print(f"   📸 검색 결과 스크린샷: demo_screenshots/stage5_search_results.png")
        
        # 테이블 찾기
        table_selectors = [
            "#tableid",  # 스크린샷에서 확인된 ID
            "#searchResult",
            "table",
            ".table-box"
        ]
        
        for selector in table_selectors:
            try:
                table = self.page.locator(selector)
                if await table.count() > 0:
                    print(f"   ✅ 테이블 발견: {selector}")
                    
                    # 테이블 하이라이트
                    await table.first.highlight()
                    await asyncio.sleep(2)
                    
                    # 테이블 내용 분석
                    rows = await table.locator('tr').all()
                    print(f"   📊 테이블 행 수: {len(rows)}")
                    
                    # 차량번호가 포함된 행 찾기
                    for i, row in enumerate(rows):
                        try:
                            row_text = await row.inner_text()
                            if car_number in row_text:
                                print(f"   ✅ 차량번호 발견 (행 {i}): {row_text[:100]}...")
                                await row.highlight()
                                await asyncio.sleep(2)
                                break
                        except:
                            continue
                    
                    break
            except Exception:
                continue
        
        # 최종 결과 스크린샷
        await self.page.screenshot(path="demo_screenshots/stage5_final_result.png")
        print(f"   📸 최종 결과 스크린샷: demo_screenshots/stage5_final_result.png")
    
    async def cleanup(self):
        """정리"""
        print("\n🧹 브라우저 정리 중...")
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        print("✅ 정리 완료")

async def main():
    """메인 데모 실행"""
    demo = CStoreDemo()
    
    try:
        # 스크린샷 디렉토리 생성
        import os
        os.makedirs("demo_screenshots", exist_ok=True)
        
        await demo.setup_browser()
        await demo.demonstrate_stages()
        
        print("\n🎉 C 매장 크롤러 구성 단계 시연 완료!")
        print("📁 스크린샷은 demo_screenshots/ 폴더에 저장되었습니다.")
        
        # 결과 확인을 위해 대기
        input("\n결과 확인 후 Enter를 눌러 종료...")
        
    except Exception as e:
        print(f"데모 실행 중 오류: {str(e)}")
    finally:
        await demo.cleanup()

if __name__ == "__main__":
    asyncio.run(main())