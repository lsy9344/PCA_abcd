"""
C 매장 페이지 요소 분석 및 셀렉터 찾기
"""
import asyncio
from playwright.async_api import async_playwright
import yaml
from pathlib import Path
import os

class CStoreSelectorDebugger:
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
        """브라우저 초기화"""
        print("🚀 디버깅용 브라우저 초기화 중...")
        
        self.playwright_instance = await async_playwright().start()
        self.browser = await self.playwright_instance.chromium.launch(
            headless=False,
            slow_mo=500,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        self.context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 800}
        )
        
        self.page = await self.context.new_page()
        self.page.set_default_timeout(30000)
        
        print("✅ 브라우저 초기화 완료")
    
    async def analyze_login_page(self):
        """로그인 페이지 요소 분석"""
        print("🔍 로그인 페이지 요소 분석 시작")
        
        try:
            # 사이트 접속
            await self.page.goto(self.config['store']['website_url'])
            await self.page.wait_for_load_state('networkidle')
            
            print(f"✅ 사이트 접속: {self.page.url}")
            
            # 모든 input 요소 찾기
            print("\n📋 페이지의 모든 input 요소:")
            inputs = await self.page.locator('input').all()
            for i, input_elem in enumerate(inputs):
                try:
                    tag_name = await input_elem.get_attribute('type') or 'text'
                    placeholder = await input_elem.get_attribute('placeholder') or ''
                    id_attr = await input_elem.get_attribute('id') or ''
                    name_attr = await input_elem.get_attribute('name') or ''
                    class_attr = await input_elem.get_attribute('class') or ''
                    
                    print(f"  {i+1}. type='{tag_name}' placeholder='{placeholder}' id='{id_attr}' name='{name_attr}' class='{class_attr}'")
                except:
                    continue
            
            # 모든 button 요소 찾기
            print("\n📋 페이지의 모든 button 요소:")
            buttons = await self.page.locator('button').all()
            for i, button in enumerate(buttons):
                try:
                    text = await button.inner_text()
                    id_attr = await button.get_attribute('id') or ''
                    class_attr = await button.get_attribute('class') or ''
                    type_attr = await button.get_attribute('type') or ''
                    
                    print(f"  {i+1}. text='{text}' id='{id_attr}' class='{class_attr}' type='{type_attr}'")
                except:
                    continue
            
            # 모든 div 요소 중 클릭 가능한 것들 찾기
            print("\n📋 클릭 가능한 div 요소들 ('로그인' 텍스트 포함):")
            divs_with_login = await self.page.locator('div:has-text("로그인")').all()
            for i, div in enumerate(divs_with_login):
                try:
                    text = await div.inner_text()
                    id_attr = await div.get_attribute('id') or ''
                    class_attr = await div.get_attribute('class') or ''
                    onclick = await div.get_attribute('onclick') or ''
                    
                    print(f"  {i+1}. text='{text.strip()}' id='{id_attr}' class='{class_attr}' onclick='{onclick}'")
                except:
                    continue
            
            # span 요소도 확인
            print("\n📋 span 요소들 ('로그인' 텍스트 포함):")
            spans_with_login = await self.page.locator('span:has-text("로그인")').all()
            for i, span in enumerate(spans_with_login):
                try:
                    text = await span.inner_text()
                    id_attr = await span.get_attribute('id') or ''
                    class_attr = await span.get_attribute('class') or ''
                    onclick = await span.get_attribute('onclick') or ''
                    
                    print(f"  {i+1}. text='{text.strip()}' id='{id_attr}' class='{class_attr}' onclick='{onclick}'")
                except:
                    continue
            
            # 전체 HTML 구조 확인 (form 요소 찾기)
            print("\n📋 form 요소 분석:")
            forms = await self.page.locator('form').all()
            for i, form in enumerate(forms):
                try:
                    action = await form.get_attribute('action') or ''
                    method = await form.get_attribute('method') or ''
                    class_attr = await form.get_attribute('class') or ''
                    
                    print(f"  {i+1}. action='{action}' method='{method}' class='{class_attr}'")
                    
                    # form 내부 요소들
                    form_inputs = await form.locator('input').all()
                    form_buttons = await form.locator('button').all()
                    
                    print(f"    - input 개수: {len(form_inputs)}")
                    print(f"    - button 개수: {len(form_buttons)}")
                    
                except:
                    continue
            
            # 스크린샷 저장
            await self.page.screenshot(path="debug_screenshots/login_page_analysis.png")
            print(f"\n📸 분석 스크린샷 저장: debug_screenshots/login_page_analysis.png")
            
            # 실제 요소 테스트
            await self._test_selectors()
            
        except Exception as e:
            print(f"❌ 분석 중 오류: {str(e)}")
    
    async def _test_selectors(self):
        """다양한 셀렉터 테스트"""
        print("\n🧪 셀렉터 테스트:")
        
        # 사용자명 입력란 테스트
        username_selectors = [
            "input[placeholder='아이디를 입력해주세요.']",
            "input[type='text']",
            "input:first-of-type",
            "[placeholder*='아이디']",
            "input[name='username']",
            "input[name='userid']",
            "#userid",
            "#username"
        ]
        
        print("  📝 사용자명 입력란 셀렉터 테스트:")
        for selector in username_selectors:
            try:
                count = await self.page.locator(selector).count()
                if count > 0:
                    print(f"    ✅ {selector} - 찾음 ({count}개)")
                else:
                    print(f"    ❌ {selector} - 없음")
            except:
                print(f"    ⚠️  {selector} - 오류")
        
        # 비밀번호 입력란 테스트
        password_selectors = [
            "input[placeholder='비밀번호를 입력해주세요.']",
            "input[type='password']",
            "[placeholder*='비밀번호']",
            "input[name='password']",
            "#password"
        ]
        
        print("  🔒 비밀번호 입력란 셀렉터 테스트:")
        for selector in password_selectors:
            try:
                count = await self.page.locator(selector).count()
                if count > 0:
                    print(f"    ✅ {selector} - 찾음 ({count}개)")
                else:
                    print(f"    ❌ {selector} - 없음")
            except:
                print(f"    ⚠️  {selector} - 오류")
        
        # 로그인 버튼 테스트
        button_selectors = [
            "button:has-text('로그인')",
            "button",
            "input[type='submit']",
            "input[value='로그인']",
            "[type='submit']",
            "button[type='submit']",
            ".login-btn",
            "#loginBtn",
            "div:has-text('로그인')",
            "span:has-text('로그인')",
            "[onclick*='login']",
            "[onclick*='Login']",
            ".btn",
            ".button"
        ]
        
        print("  🔘 로그인 버튼 셀렉터 테스트:")
        for selector in button_selectors:
            try:
                count = await self.page.locator(selector).count()
                if count > 0:
                    print(f"    ✅ {selector} - 찾음 ({count}개)")
                    # 버튼 텍스트도 확인
                    try:
                        text = await self.page.locator(selector).first.inner_text()
                        print(f"       텍스트: '{text}'")
                    except:
                        pass
                else:
                    print(f"    ❌ {selector} - 없음")
            except:
                print(f"    ⚠️  {selector} - 오류")
    
    async def test_login_flow(self):
        """실제 로그인 흐름 테스트"""
        print("\n🔄 실제 로그인 흐름 테스트")
        
        try:
            # 정확한 셀렉터들로 테스트
            username_input = self.page.locator("#user_id")
            password_input = self.page.locator("#pwd")
            
            # 로그인 버튼 후보들
            login_button_candidates = [
                self.page.locator("div:has-text('로그인')"),
                self.page.locator("span:has-text('로그인')"),
                self.page.locator("[onclick*='login']"),
                self.page.locator("[onclick*='Login']")
            ]
            
            # 사용자명 입력
            if await username_input.count() > 0:
                await username_input.fill(self.config['login']['username'])
                print(f"  ✅ 사용자명 입력 완료: {self.config['login']['username']}")
            
            # 비밀번호 입력
            if await password_input.count() > 0:
                await password_input.fill(self.config['login']['password'])
                print(f"  ✅ 비밀번호 입력 완료")
            
            # 입력 후 스크린샷
            await self.page.screenshot(path="debug_screenshots/login_filled.png")
            print(f"  📸 입력 완료 스크린샷: debug_screenshots/login_filled.png")
            
            # 로그인 버튼 클릭 시도
            login_success = False
            for i, candidate in enumerate(login_button_candidates):
                try:
                    if await candidate.count() > 0:
                        print(f"  🔍 로그인 버튼 후보 {i+1} 시도 중...")
                        await candidate.first.click()
                        print(f"  ✅ 로그인 버튼 클릭 완료 (후보 {i+1})")
                        login_success = True
                        break
                except Exception as e:
                    print(f"  ❌ 로그인 버튼 후보 {i+1} 실패: {str(e)}")
                    continue
            
            if login_success:
                # 로그인 후 대기
                await self.page.wait_for_timeout(5000)
                
                # 로그인 후 상태 확인
                current_url = self.page.url
                print(f"  📍 로그인 후 URL: {current_url}")
                
                # 스크린샷 저장
                await self.page.screenshot(path="debug_screenshots/after_login.png")
                print(f"  📸 로그인 후 스크린샷: debug_screenshots/after_login.png")
            else:
                print(f"  ❌ 모든 로그인 버튼 후보 실패")
            
        except Exception as e:
            print(f"  ❌ 로그인 테스트 실패: {str(e)}")
    
    async def cleanup(self):
        """리소스 정리"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright_instance:
                await self.playwright_instance.stop()
        except Exception as e:
            print(f"정리 중 오류: {str(e)}")

async def main():
    """메인 디버깅 실행"""
    # 디버그 스크린샷 디렉토리 생성
    os.makedirs("debug_screenshots", exist_ok=True)
    
    debugger = CStoreSelectorDebugger()
    
    try:
        await debugger.setup_browser()
        await debugger.analyze_login_page()
        await debugger.test_login_flow()
        
        print("\n🎉 분석 완료!")
        print("📁 스크린샷은 debug_screenshots/ 폴더에 저장되었습니다.")
        
        # 결과 확인을 위해 브라우저 유지
        input("\n브라우저를 닫으려면 Enter를 누르세요...")
        
    except Exception as e:
        print(f"❌ 디버깅 중 오류: {str(e)}")
    finally:
        await debugger.cleanup()

if __name__ == "__main__":
    asyncio.run(main())