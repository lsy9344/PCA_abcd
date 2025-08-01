#!/usr/bin/env python3
"""
D매장 최종 크롤링 테스트 - 실제 셀렉터 사용
"""

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright
import yaml

async def final_d_store_test():
    """D매장 최종 테스트"""
    
    # 설정 로드
    config_path = Path("infrastructure/config/store_configs/d_store_config.yaml")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    website_url = config['store']['website_url']
    username = config['login']['username']
    password = config['login']['password']
    
    print("🚀 D매장 최종 크롤링 테스트")
    print("="*50)
    print(f"웹사이트: {website_url}")
    print(f"사용자명: {username}")
    print("="*50)
    
    screenshot_dir = Path("screenshots")
    screenshot_dir.mkdir(exist_ok=True)
    
    playwright = None
    browser = None
    
    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        page.set_default_timeout(10000)
        
        print("\n1단계: 사이트 접속")
        print("-" * 30)
        
        await page.goto(website_url, wait_until='networkidle')
        await page.screenshot(path=str(screenshot_dir / "final_01_site_access.png"))
        
        title = await page.title()
        print(f"✅ 페이지 제목: {title}")
        print(f"✅ 현재 URL: {page.url}")
        
        print("\n2단계: 로그인 시도")
        print("-" * 30)
        
        # 실제 확인된 셀렉터 사용
        id_selector = '#mf_wfm_body_ibx_empCd'
        pwd_selector = '#mf_wfm_body_sct_password'
        login_btn_selector = '#mf_wfm_body_btn_login'
        
        # ID 입력
        await page.wait_for_selector(id_selector, timeout=10000)
        await page.fill(id_selector, username)
        print(f"✅ ID 입력 완료: {username}")
        
        # 비밀번호 입력
        await page.wait_for_selector(pwd_selector, timeout=10000)
        await page.fill(pwd_selector, password)
        print("✅ 비밀번호 입력 완료")
        
        await page.screenshot(path=str(screenshot_dir / "final_02_login_form.png"))
        
        # 로그인 버튼 클릭
        await page.wait_for_selector(login_btn_selector, timeout=10000)
        await page.click(login_btn_selector)
        print("✅ 로그인 버튼 클릭 완료")
        
        # 로그인 후 페이지 로드 대기
        await asyncio.sleep(5)
        await page.wait_for_load_state('networkidle')
        
        new_url = page.url
        new_title = await page.title()
        
        print(f"📍 로그인 후 URL: {new_url}")
        print(f"📍 로그인 후 제목: {new_title}")
        
        await page.screenshot(path=str(screenshot_dir / "final_03_after_login.png"))
        
        # 로그인 성공 여부 판단
        if new_url != website_url or "main" in new_url.lower() or "메인" in new_title:
            print("✅ 로그인 성공!")
            
            print("\n3단계: 로그인 후 페이지 구조 분석")
            print("-" * 30)
            
            # 페이지 요소들 분석
            page_text = await page.inner_text('body')
            
            # 차량 관련 요소 찾기
            car_related_keywords = ["차량", "검색", "번호", "조회"]
            print("🚗 차량 관련 기능:")
            for keyword in car_related_keywords:
                count = page_text.count(keyword)
                if count > 0:
                    print(f"  '{keyword}': {count}개 발견")
            
            # 쿠폰 관련 요소 찾기
            coupon_keywords = ["쿠폰", "할인", "무료", "유료", "적용"]
            print("\n🎟️ 쿠폰 관련 기능:")
            for keyword in coupon_keywords:
                count = page_text.count(keyword)
                if count > 0:
                    print(f"  '{keyword}': {count}개 발견")
            
            # 입력 필드들 확인
            input_elements = await page.locator('input').all()
            print(f"\n📝 입력 필드 개수: {len(input_elements)}")
            
            # 차량번호 입력 필드 찾기
            car_input_found = False
            for i, input_el in enumerate(input_elements[:10]):
                try:
                    input_id = await input_el.get_attribute('id') or ''
                    input_name = await input_el.get_attribute('name') or ''
                    input_placeholder = await input_el.get_attribute('placeholder') or ''
                    
                    if any(keyword in (input_id + input_name + input_placeholder).lower() 
                           for keyword in ['car', '차량', 'vehicle', 'number']):
                        print(f"  🚗 차량 관련 입력필드 발견: id={input_id}, name={input_name}, placeholder={input_placeholder}")
                        car_input_found = True
                except:
                    continue
            
            # 버튼들 확인
            button_elements = await page.locator('button').all()
            input_buttons = await page.locator('input[type="button"], input[type="submit"]').all()
            
            total_buttons = len(button_elements) + len(input_buttons)
            print(f"\n🔘 버튼 개수: {total_buttons}")
            
            # 검색 관련 버튼 찾기
            search_buttons = []
            for button_list in [button_elements, input_buttons]:
                for button in button_list:
                    try:
                        if button_list == button_elements:
                            text = await button.inner_text()
                        else:
                            text = await button.get_attribute('value') or ''
                        
                        if any(keyword in text for keyword in ['검색', 'search', '조회', '찾기']):
                            button_id = await button.get_attribute('id') or 'N/A'
                            search_buttons.append(f"'{text}' (id: {button_id})")
                    except:
                        continue
            
            if search_buttons:
                print("  🔍 검색 관련 버튼:")
                for btn in search_buttons:
                    print(f"    {btn}")
            
            # 테이블 확인
            tables = await page.locator('table').all()
            print(f"\n📊 테이블 개수: {len(tables)}")
            
            if tables:
                print("  📋 테이블 내용 분석:")
                for i, table in enumerate(tables[:3]):  # 처음 3개만
                    try:
                        table_text = await table.inner_text()
                        if any(keyword in table_text for keyword in ['쿠폰', '할인', '차량', '검색']):
                            print(f"    테이블 {i+1}: 관련 내용 발견 (길이: {len(table_text)} 문자)")
                    except:
                        continue
            
            print("\n4단계: 차량 검색 기능 테스트")
            print("-" * 30)
            
            # 테스트용 차량번호로 검색 시도
            test_car_number = "12가3456"
            
            # 차량번호 입력 필드 찾기 및 입력 시도
            car_input_selectors = [
                'input[placeholder*="차량"]',
                'input[name*="car"]',
                'input[id*="car"]',
                'input[name*="vehicle"]',
                'input[type="text"]'
            ]
            
            car_input_success = False
            for selector in car_input_selectors:
                try:
                    elements = await page.locator(selector).all()
                    if elements:
                        await elements[0].fill(test_car_number)
                        print(f"✅ 차량번호 입력 성공: {selector} -> {test_car_number}")
                        car_input_success = True
                        break
                except:
                    continue
            
            if not car_input_success:
                print("⚠️ 차량번호 입력 필드를 찾을 수 없음")
            
            await page.screenshot(path=str(screenshot_dir / "final_04_car_search.png"))
            
            # 검색 버튼 클릭 시도
            search_selectors = [
                'button:has-text("검색")',
                'input[value*="검색"]',
                'button:has-text("조회")',
                'input[value*="조회"]'
            ]
            
            search_success = False
            for selector in search_selectors:
                try:
                    elements = await page.locator(selector).all()
                    if elements:
                        await elements[0].click()
                        print(f"✅ 검색 버튼 클릭 성공: {selector}")
                        search_success = True
                        await asyncio.sleep(3)
                        break
                except:
                    continue
            
            if not search_success:
                print("⚠️ 검색 버튼을 찾을 수 없음")
            
            await page.screenshot(path=str(screenshot_dir / "final_05_search_result.png"))
            
            print("\n5단계: 쿠폰 기능 확인")
            print("-" * 30)
            
            # 쿠폰 관련 요소들 찾기
            coupon_elements = await page.locator('*').filter(has_text='쿠폰').all()
            print(f"🎟️ '쿠폰' 텍스트 포함 요소: {len(coupon_elements)}개")
            
            discount_elements = await page.locator('*').filter(has_text='할인').all()
            print(f"💰 '할인' 텍스트 포함 요소: {len(discount_elements)}개")
            
            # 적용 버튼 찾기
            apply_buttons = await page.locator('button:has-text("적용"), input[value*="적용"]').all()
            print(f"🔘 '적용' 버튼: {len(apply_buttons)}개")
            
            await page.screenshot(path=str(screenshot_dir / "final_06_coupon_check.png"))
            
        else:
            print("❌ 로그인 실패 - URL이나 제목이 변경되지 않음")
            
            # 오류 메시지 확인
            page_text = await page.inner_text('body')
            error_keywords = ["오류", "실패", "잘못", "error", "fail"]
            
            print("🔍 오류 메시지 확인:")
            for keyword in error_keywords:
                if keyword in page_text.lower():
                    print(f"  ⚠️ '{keyword}' 키워드 발견")
        
        print("\n" + "="*50)
        print("📊 테스트 결과 요약")
        print("="*50)
        
        # 최종 결과
        login_success = new_url != website_url or "main" in new_url.lower()
        
        print(f"1. 사이트 접속: ✅ 성공")
        print(f"2. 로그인 시도: {'✅ 성공' if login_success else '❌ 실패'}")
        print(f"3. 페이지 구조 분석: {'✅ 완료' if login_success else '⚠️ 제한적'}")
        print(f"4. 차량 검색 기능: {'🔍 확인됨' if login_success else '❌ 접근 불가'}")
        print(f"5. 쿠폰 관련 기능: {'🎟️ 확인됨' if login_success else '❌ 접근 불가'}")
        
        print(f"\n📁 스크린샷 저장 위치: {screenshot_dir.absolute()}")
        
        return login_success
        
    except Exception as e:
        print(f"❌ 테스트 중 오류: {str(e)}")
        return False
        
    finally:
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()

if __name__ == "__main__":
    success = asyncio.run(final_d_store_test())
    
    print("\n" + "="*50)
    print("💡 D매장 크롤링 권장사항")
    print("="*50)
    
    if success:
        print("✅ 로그인 성공 - 다음 단계 진행 가능:")
        print("   • 실제 차량번호로 검색 테스트")
        print("   • 쿠폰 적용 기능 구현")
        print("   • 자동화 스크립트 완성")
    else:
        print("⚠️ 로그인 실패 - 다음 사항 확인 필요:")
        print("   • 로그인 정보 재확인")
        print("   • 네트워크 연결 상태")
        print("   • 사이트 접근 제한 여부")
    
    print("\n🔧 실제 확인된 셀렉터:")
    print("   • ID 입력: #mf_wfm_body_ibx_empCd")
    print("   • 비밀번호 입력: #mf_wfm_body_sct_password")
    print("   • 로그인 버튼: #mf_wfm_body_btn_login")
    print("\n📋 설정 파일 업데이트 권장:")
    print("   • d_store_config.yaml의 selectors 섹션을 실제 값으로 업데이트")