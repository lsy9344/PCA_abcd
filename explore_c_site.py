#!/usr/bin/env python3
"""
C 사이트 탐색 스크립트 - 로그인 및 차량번호 입력
"""
import asyncio
from playwright.async_api import async_playwright

async def explore_c_site():
    """C 사이트 로그인 및 차량번호 입력 테스트"""
    
    async with async_playwright() as p:
        # 브라우저 실행 (headless=False로 화면 보이게)
        browser = await p.chromium.launch(headless=False, slow_mo=1000)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            print("🌐 C 사이트(g048.gparking.kr) 접속 중...")
            await page.goto("http://g048.gparking.kr")
            await page.wait_for_load_state('networkidle')
            
            print(f"✅ 페이지 로드 완료: {page.url}")
            print(f"페이지 제목: {await page.title()}")
            
            # 페이지 HTML 구조 간단히 확인
            body_content = await page.locator('body').inner_html()
            print(f"📄 페이지 본문 길이: {len(body_content)} characters")
            if len(body_content) < 500:
                print(f"📄 페이지 HTML (처음 500자): {body_content[:500]}")
            
            # 1단계: 로그인 필드 찾기 및 입력
            print("\n🔍 로그인 필드를 찾는 중...")
            
            # 다양한 로그인 필드 선택자 시도
            login_selectors = [
                '#userid', '#id', '#loginId', '#user_id', '#username',
                'input[name="userid"]', 'input[name="id"]', 'input[name="username"]',
                'input[type="text"]'
            ]
            
            username_field = None
            for selector in login_selectors:
                try:
                    field = page.locator(selector).first
                    if await field.count() > 0:
                        username_field = field
                        print(f"✅ 사용자명 필드 발견: {selector}")
                        break
                except:
                    continue
            
            if not username_field:
                # 모든 input 필드 확인
                all_inputs = await page.locator('input').all()
                print(f"📝 페이지의 모든 input 필드 ({len(all_inputs)}개):")
                for i, input_field in enumerate(all_inputs):
                    input_id = await input_field.get_attribute('id')
                    input_name = await input_field.get_attribute('name')
                    input_type = await input_field.get_attribute('type')
                    input_placeholder = await input_field.get_attribute('placeholder')
                    print(f"  {i+1}. ID: {input_id}, Name: {input_name}, Type: {input_type}, Placeholder: {input_placeholder}")
                
                # 첫 번째 텍스트 입력 필드를 사용자명 필드로 추정
                text_inputs = [inp for inp in all_inputs if await inp.get_attribute('type') in ['text', None]]
                if text_inputs:
                    username_field = text_inputs[0]
                    print("✅ 첫 번째 텍스트 필드를 사용자명 필드로 사용")
            
            # 패스워드 필드 찾기
            password_selectors = [
                '#password', '#passwd', '#pwd', '#loginPw', '#user_pw',
                'input[name="password"]', 'input[name="passwd"]', 'input[name="pwd"]',
                'input[type="password"]'
            ]
            
            password_field = None
            for selector in password_selectors:
                try:
                    field = page.locator(selector).first
                    if await field.count() > 0:
                        password_field = field
                        print(f"✅ 패스워드 필드 발견: {selector}")
                        break
                except:
                    continue
            
            if not password_field:
                # password type 필드 찾기
                password_inputs = await page.locator('input[type="password"]').all()
                if password_inputs:
                    password_field = password_inputs[0]
                    print("✅ password type 필드를 패스워드 필드로 사용")
            
            # 로그인 정보 입력
            if username_field and password_field:
                print("\n📝 로그인 정보 입력 중...")
                await username_field.fill("1024")
                print("✅ 사용자명 입력 완료: 1024")
                
                await password_field.fill("1211")
                print("✅ 패스워드 입력 완료: 1211")
                
                # 로그인 버튼 찾기 및 클릭
                login_button_selectors = [
                    '#loginBtn', '#login', '#btn_login', '#submit',
                    'button:has-text("로그인")', 'button:has-text("LOGIN")',
                    'input[type="submit"]', 'input[value*="로그인"]'
                ]
                
                login_button = None
                for selector in login_button_selectors:
                    try:
                        btn = page.locator(selector).first
                        if await btn.count() > 0:
                            login_button = btn
                            print(f"✅ 로그인 버튼 발견: {selector}")
                            break
                    except:
                        continue
                
                if not login_button:
                    # 모든 버튼과 클릭 가능한 요소 확인
                    all_buttons = await page.locator('button, input[type="submit"], input[type="button"], a, div[onclick], span[onclick]').all()
                    print(f"🔘 페이지의 모든 클릭 가능한 요소 ({len(all_buttons)}개):")
                    for i, button in enumerate(all_buttons):
                        button_text = await button.inner_text()
                        button_id = await button.get_attribute('id')
                        button_class = await button.get_attribute('class')
                        button_type = await button.get_attribute('type')
                        button_onclick = await button.get_attribute('onclick')
                        tag_name = await button.evaluate('el => el.tagName')
                        print(f"  {i+1}. 태그: {tag_name}, 텍스트: '{button_text}', ID: {button_id}, Class: {button_class}, Type: {button_type}, Onclick: {button_onclick}")
                        
                        # 로그인 관련 텍스트나 클래스가 있으면 시도 (단, '닫기'는 제외)
                        if ('로그인' in str(button_text).lower() or 'login' in str(button_text).lower()) and \
                           '닫기' not in str(button_text):
                            login_button = button
                            print(f"✅ 로그인 버튼으로 추정: {tag_name} - '{button_text}'")
                
                if login_button:
                    print("\n🔐 로그인 시도 중...")
                    await login_button.click()
                    await page.wait_for_load_state('networkidle')
                    print("✅ 로그인 버튼 클릭 완료")
                    
                    # 로그인 성공 확인 (URL 변경 또는 특정 요소 확인)
                    await asyncio.sleep(2)
                    current_url = page.url
                    print(f"현재 URL: {current_url}")
                    
                    # 2단계: 차량번호 입력 필드 찾기
                    print("\n🚗 차량번호 입력 필드를 찾는 중...")
                    
                    car_number_selectors = [
                        '#carNo', '#carNumber', '#car_number', '#vehicleNo',
                        'input[name="carNo"]', 'input[name="carNumber"]', 'input[name="car_number"]',
                        'input[placeholder*="차량"]', 'input[placeholder*="번호"]'
                    ]
                    
                    car_number_field = None
                    for selector in car_number_selectors:
                        try:
                            field = page.locator(selector).first
                            if await field.count() > 0:
                                car_number_field = field
                                print(f"✅ 차량번호 필드 발견: {selector}")
                                break
                        except:
                            continue
                    
                    if not car_number_field:
                        # 로그인 후 모든 input 필드 다시 확인
                        all_inputs_after_login = await page.locator('input').all()
                        print(f"📝 로그인 후 모든 input 필드 ({len(all_inputs_after_login)}개):")
                        for i, input_field in enumerate(all_inputs_after_login):
                            input_id = await input_field.get_attribute('id')
                            input_name = await input_field.get_attribute('name')
                            input_type = await input_field.get_attribute('type')
                            input_placeholder = await input_field.get_attribute('placeholder')
                            print(f"  {i+1}. ID: {input_id}, Name: {input_name}, Type: {input_type}, Placeholder: {input_placeholder}")
                        
                        # 텍스트 입력 필드 중에서 차량번호 필드로 추정되는 것 선택
                        text_inputs_after_login = [inp for inp in all_inputs_after_login 
                                                 if await inp.get_attribute('type') in ['text', None]]
                        if text_inputs_after_login:
                            car_number_field = text_inputs_after_login[0]
                            print("✅ 첫 번째 텍스트 필드를 차량번호 필드로 사용")
                    
                    if car_number_field:
                        print("\n🚗 차량번호 입력 중...")
                        await car_number_field.fill("6897")
                        print("✅ 차량번호 입력 완료: 6897")
                        
                        # 검색 버튼 찾기
                        search_button_selectors = [
                            '#searchBtn', '#search', '#btn_search',
                            'button:has-text("검색")', 'button:has-text("조회")',
                            'input[type="submit"]', 'input[value*="검색"]'
                        ]
                        
                        search_button = None
                        for selector in search_button_selectors:
                            try:
                                btn = page.locator(selector).first
                                if await btn.count() > 0:
                                    search_button = btn
                                    print(f"✅ 검색 버튼 발견: {selector}")
                                    break
                            except:
                                continue
                        
                        if not search_button:
                            # 로그인 후 모든 클릭 가능한 요소 다시 확인
                            all_buttons_after_login = await page.locator('button, input[type="submit"], input[type="button"], a, div[onclick], span[onclick], img[onclick]').all()
                            print(f"🔘 로그인 후 모든 클릭 가능한 요소 ({len(all_buttons_after_login)}개):")
                            for i, button in enumerate(all_buttons_after_login):
                                button_text = await button.inner_text()
                                button_id = await button.get_attribute('id')
                                button_class = await button.get_attribute('class')
                                button_type = await button.get_attribute('type')
                                button_onclick = await button.get_attribute('onclick')
                                tag_name = await button.evaluate('el => el.tagName')
                                print(f"  {i+1}. 태그: {tag_name}, 텍스트: '{button_text}', ID: {button_id}, Class: {button_class}, Type: {button_type}, Onclick: {button_onclick}")
                                
                                # 검색 관련 키워드 확인
                                if any(keyword in str(button_text).lower() for keyword in ['검색', 'search', '조회', '찾기']) or \
                                   any(keyword in str(button_onclick).lower() for keyword in ['search', 'find']) if button_onclick else False:
                                    search_button = button
                                    print(f"✅ 검색 버튼으로 추정: {tag_name} - '{button_text}'")
                        
                        if search_button:
                            print("\n🔍 차량 검색 시도 중...")
                            await search_button.click()
                            await page.wait_for_load_state('networkidle')
                            print("✅ 검색 버튼 클릭 완료")
                            
                            # 검색 결과 확인
                            await asyncio.sleep(2)
                            print(f"검색 후 URL: {page.url}")
                            
                            # 검색 결과나 오류 메시지 확인
                            error_messages = await page.locator('text*="검색된"').all()
                            if error_messages:
                                for msg in error_messages:
                                    msg_text = await msg.inner_text()
                                    print(f"📋 메시지: {msg_text}")
                            
                            # 페이지 전체 텍스트에서 쿠폰 관련 키워드 찾기
                            page_content = await page.content()
                            coupon_keywords = ["쿠폰", "할인", "적용", "이용권", "권", "시간"]
                            found_keywords = [kw for kw in coupon_keywords if kw in page_content]
                            if found_keywords:
                                print(f"🎫 쿠폰 관련 키워드 발견: {found_keywords}")
                        else:
                            print("❌ 검색 버튼을 찾을 수 없습니다")
                    else:
                        print("❌ 차량번호 입력 필드를 찾을 수 없습니다")
                else:
                    print("❌ 로그인 버튼을 찾을 수 없습니다")
            else:
                print("❌ 로그인 필드를 찾을 수 없습니다")
                print(f"사용자명 필드: {username_field is not None}")
                print(f"패스워드 필드: {password_field is not None}")
            
            print("\n📸 현재 페이지 상태:")
            print(f"URL: {page.url}")
            print(f"제목: {await page.title()}")
            
            # 잠시 대기 (수동으로 페이지 확인 가능)
            print("\n⏱️  15초 대기 중... (페이지 상태 확인 가능)")
            await asyncio.sleep(15)
            
        except Exception as e:
            print(f"❌ 오류 발생: {str(e)}")
            import traceback
            traceback.print_exc()
            
        finally:
            await browser.close()
            print("🚪 브라우저 종료")

if __name__ == "__main__":
    asyncio.run(explore_c_site())