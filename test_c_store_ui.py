"""
C 매장 로그인 → 차량번호 입력 → 차량조회 버튼 클릭 → 테이블에서 차량 선택 → 쿠폰 적용 기능 테스트
할인 로직에 따른 적절한 쿠폰 조합 계산 및 적용
"""
import asyncio
from playwright.async_api import async_playwright
import yaml
from pathlib import Path
import os
from datetime import datetime, date
import calendar
import sys
sys.path.append('.')
from shared.utils.common_coupon_calculator import CommonCouponCalculator, StoreConfig
from infrastructure.notifications.telegram_adapter import TelegramAdapter
from infrastructure.logging.structured_logger import StructuredLogger
from core.application.dto.automation_dto import ErrorContext


class CStoreUITest:
    def __init__(self):
        self.page = None
        self.browser = None
        self.context = None
        self.playwright_instance = None
        
        self.config = self._load_config()
        self.coupon_history = {"my_history": {}, "total_history": {}}
        self.is_weekday = self._check_if_weekday()
        
        # 로그인 정보 yaml 파일에서 로드 (A, B 매장과 동일하게)
        if 'login' not in self.config:
            raise ValueError("C매장 로그인 정보가 설정 파일에 없습니다. c_store_config.yaml 파일을 확인하세요.")
        
        self.username = self.config['login']['username']
        self.password = self.config['login']['password']
        
        # 텔레그램 알림 서비스 초기화
        self.notification_service = None
        self.logger = None
        self._initialize_notification_service()
        
    def _load_config(self):
        """C 매장 설정 로드"""
        config_path = Path("infrastructure/config/store_configs/c_store_config.yaml")
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _check_if_weekday(self):
        """오늘이 평일인지 확인 (월~금, 공휴일 제외)"""
        today = date.today()
        # 0=월요일, 6=일요일
        weekday = today.weekday()
        return weekday < 5  # 월~금 (0~4)
    
    def _initialize_notification_service(self):
        """텔레그램 알림 서비스 초기화"""
        try:
            # 베이스 설정 로드
            base_config_path = Path("infrastructure/config/base_config.yaml")
            if base_config_path.exists():
                with open(base_config_path, 'r', encoding='utf-8') as f:
                    base_config = yaml.safe_load(f)
                
                telegram_config = base_config.get('telegram', {})
                if telegram_config.get('bot_token') and telegram_config.get('chat_id'):
                    log_config = base_config.get('logging', {'level': 'INFO'})
                    self.logger = StructuredLogger("test_c_store_ui", log_config)
                    self.notification_service = TelegramAdapter(telegram_config, self.logger)
                    print("   ✅ 텔레그램 알림 서비스 초기화 완료")
                else:
                    print("   ⚠️ 텔레그램 설정이 없어 알림 기능이 비활성화됩니다")
            else:
                print("   ⚠️ base_config.yaml 파일을 찾을 수 없어 알림 기능이 비활성화됩니다")
        except Exception as e:
            print(f"   ⚠️ 텔레그램 알림 서비스 초기화 실패: {str(e)}")
    
    async def _parse_current_applied_coupons(self):
        """현재 적용된 쿠폰 파싱 (C 매장: total_history만 사용)"""
        try:
            # C 매장 설정 가져오기
            store_config = StoreConfig.get_coupon_config("C")
            
            # 할인 내역 테이블이 로드될 때까지 대기
            try:
                await self.page.wait_for_selector("tbody[id='discountlist']", timeout=5000)
                print("     ✅ 할인 내역 테이블 로드 확인")
            except:
                print("     ⚠️ 할인 내역 테이블을 찾을 수 없음")
            
            # 공통 유틸리티로 파싱 (C 매장은 my_history 사용 안함)
            my_history, total_history = await CommonCouponCalculator.parse_applied_coupons(
                self.page,
                store_config["coupon_key_mapping"],
                store_config["discount_selectors"],
                has_my_history=store_config.get("has_my_history", True)
            )
            
            # C 매장 특성: my_history는 항상 빈 딕셔너리
            my_history = {}
            
            # 쿠폰 히스토리 업데이트
            self.coupon_history["my_history"] = my_history
            self.coupon_history["total_history"] = total_history
            
            return my_history, total_history
            
        except Exception as e:
            print(f"   ⚠️ 현재 쿠폰 파싱 실패: {str(e)}")
            return {}, {}

    def _calculate_required_coupons(self, my_history=None, total_history=None):
        """할인 규칙에 따른 필요 쿠폰 계산 (현재 적용된 쿠폰 차감)"""
        
        # 기본값 설정
        if my_history is None:
            my_history = self.coupon_history["my_history"]
        if total_history is None:
            total_history = self.coupon_history["total_history"]
            
        discount_types = self.config['coupons']
        
        # 쿠폰 키 매핑 (C 매장)
        free_key = "FREE_2HOUR"  # C 매장은 2시간 무료 쿠폰
        paid_1hour_key = "PAID_1HOUR"
        
        # 현재 적용된 쿠폰 수 (파싱된 결과 사용)
        free_current = my_history.get(free_key, 0)
        paid_1hour_current = my_history.get(paid_1hour_key, 0)
        
        # C 매장 특성: total_history의 모든 쿠폰이 현재 적용된 쿠폰
        # total_history에서 각 쿠폰 개수 추출 (C 매장은 my_history 사용 안함)
        free_current = total_history.get(free_key, 0)
        paid_1hour_current = total_history.get(paid_1hour_key, 0)
        
        # 전체 무료 쿠폰 사용 이력은 total_history와 동일
        total_free_used = total_history.get(free_key, 0)
        
        if self.is_weekday:
            # 평일: 총 3시간 목표 (180분)
            target_minutes = 180
            print(f"   📅 평일 모드: {target_minutes//60}시간 할인 목표")
            
            # 현재 적용된 총 할인 시간 계산 (분 단위) - total_history 기준
            current_minutes = 0
            current_minutes += free_current * 120  # 2시간 무료 쿠폰
            current_minutes += paid_1hour_current * 60  # 1시간 유료 쿠폰
            
            print(f"   📊 현재 적용된 할인: {current_minutes}분 (무료 2시간: {free_current}개, 유료 1시간: {paid_1hour_current}개)")
            
            # 남은 시간 계산
            remaining_minutes = max(0, target_minutes - current_minutes)
            print(f"   📊 추가 필요 할인: {remaining_minutes}분")
            
            if remaining_minutes == 0:
                print(f"   ✅ 목표 할인 시간 달성 - 추가 쿠폰 불필요")
                return {free_key: 0, paid_1hour_key: 0}
            
            # C 매장: 무료 쿠폰 적용 여부 결정 (이미 적용되었으면 안함)
            free_apply = 0
            if free_current == 0:  # C 매장은 total_history만 확인
                if remaining_minutes >= 120:  # 2시간 이상 필요시
                    free_apply = 1
                    remaining_minutes -= 120
            
            # 남은 시간을 1시간 유료 쿠폰으로 채우기
            paid_1hour_needed = (remaining_minutes + 59) // 60  # 올림 계산
            
            print(f"   📊 추가 적용할 쿠폰:")
            print(f"     - {free_key}: {free_apply}개")
            print(f"     - {paid_1hour_key}: {paid_1hour_needed}개")
            
            return {
                free_key: free_apply,
                paid_1hour_key: paid_1hour_needed
            }
        else:
            # 주말: 총 2시간 목표 (120분)
            target_minutes = 120
            print(f"   📅 주말 모드: {target_minutes//60}시간 할인 목표")
            
            # 현재 적용된 총 할인 시간 계산 (분 단위)
            current_minutes = 0
            current_minutes += free_current * 120  # 2시간 무료 쿠폰
            current_minutes += paid_1hour_current * 60  # 1시간 유료 쿠폰
            
            print(f"   📊 현재 적용된 할인: {current_minutes}분 (무료 2시간: {free_current}개, 유료 1시간: {paid_1hour_current}개)")
            
            # 남은 시간 계산
            remaining_minutes = max(0, target_minutes - current_minutes)
            print(f"   📊 추가 필요 할인: {remaining_minutes}분")
            
            if remaining_minutes == 0:
                print(f"   ✅ 목표 할인 시간 달성 - 추가 쿠폰 불필요")
                return {free_key: 0, paid_1hour_key: 0}
            
            # C 매장: 주말도 무료 쿠폰 적용 가능 (아직 적용 안됨)
            free_apply = 0
            if free_current == 0:  # C 매장은 total_history만 확인
                if remaining_minutes >= 120:  # 2시간 이상 필요시
                    free_apply = 1
                    remaining_minutes -= 120
            
            # 남은 시간을 1시간 유료 쿠폰으로 채우기
            paid_1hour_needed = (remaining_minutes + 59) // 60  # 올림 계산
            
            print(f"   📊 추가 적용할 쿠폰:")
            print(f"     - {free_key}: {free_apply}개")
            print(f"     - {paid_1hour_key}: {paid_1hour_needed}개")
            
            return {
                free_key: free_apply,
                paid_1hour_key: paid_1hour_needed
            }
    
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
            print("C 매장 로그인 → 차량조회 → 차량선택 → 쿠폰적용 테스트 시작")
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
            
            # 6단계: 쿠폰 적용
            if not await self._step_6_apply_coupon():
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
            # 로그인 전 페이지 상태 확인
            await self._save_screenshot("step2_before_login")
            print(f"   🔍 현재 페이지 URL: {self.page.url}")
            
            # 로그인 폼이 로드될 때까지 대기
            username_selector = self.config['selectors']['login']['username_input']
            await self.page.wait_for_selector(username_selector, timeout=10000)
            print(f"   ✅ 로그인 폼 로드 확인")
            
            # 사용자명 입력
            
            await self.page.fill(username_selector, self.username)
            print(f"   ✅ 사용자명 입력: {self.username}")
            
            # 비밀번호 입력
            password_selector = self.config['selectors']['login']['password_input']
            
            await self.page.fill(password_selector, self.password)
            print(f"   ✅ 비밀번호 입력 완료")
            
            # 로그인 버튼 클릭 (여러 셀렉터 시도)
            login_button_selectors = [
                self.config['selectors']['login']['login_button'],
                ".btn",
                "input[type='button']",
                "button:has-text('로그인')",
                "input[value='로그인']"
            ]
            
            login_clicked = False
            for selector in login_button_selectors:
                try:
                    await self.page.click(selector, timeout=5000)
                    print(f"   ✅ 로그인 버튼 클릭: {selector}")
                    login_clicked = True
                    break
                except:
                    continue
            
            if not login_clicked:
                raise Exception("로그인 버튼을 찾을 수 없습니다")
            
            # 페이지 로딩 대기
            await self.page.wait_for_timeout(3000)
            
            # 로그인 후 팝업 처리
            await self._handle_login_popups()
            
            # 로그인 성공 확인 - 차량번호 입력란 대기
            car_input_selector = self.config['selectors']['login']['car_number_input']
            await self.page.wait_for_selector(car_input_selector, timeout=15000)
            
            print(f"   ✅ 로그인 성공 확인 - 차량번호 입력란 표시됨")
            print(f"   🔍 로그인 후 URL: {self.page.url}")
            
            # 스크린샷 저장
            await self._save_screenshot("step2_login_success")
            
            return True
            
        except Exception as e:
            print(f"   ❌ 로그인 실패: {str(e)}")
            print(f"   🔍 실패 시 URL: {self.page.url}")
            
            # 페이지 내용 확인을 위한 추가 정보
            try:
                page_title = await self.page.title()
                print(f"   🔍 페이지 제목: {page_title}")
                
                # 로그인 관련 요소들 확인
                username_exists = await self.page.locator(self.config['selectors']['login']['username_input']).count()
                password_exists = await self.page.locator(self.config['selectors']['login']['password_input']).count()
                print(f"   🔍 로그인 폼 상태 - 사용자명 필드: {username_exists}개, 비밀번호 필드: {password_exists}개")
                
            except Exception as debug_error:
                print(f"   🔍 디버그 정보 수집 실패: {debug_error}")
            
            await self._save_screenshot("step2_login_failed")
            return False
    
    async def _handle_login_popups(self):
        """로그인 후 팝업 처리 (A, B 매장과 동일한 방식)"""
        try:
            popup_selectors = [
                'text=확인',
                'text=OK',
                '.popup-ok',
                '.popup-close',
                'button:has-text("확인")',
                'button:has-text("OK")',
                'input[value="확인"]'
            ]
            
            for selector in popup_selectors:
                try:
                    popup = self.page.locator(selector)
                    if await popup.count() > 0:
                        await popup.first.click()
                        await self.page.wait_for_timeout(1000)
                        print(f"   ✅ 로그인 후 팝업 처리: {selector}")
                        break
                except:
                    continue
                    
        except Exception as e:
            print(f"   ⚠️ 팝업 처리 중 오류 (계속 진행): {str(e)}")
    
    async def _step_3_input_vehicle(self):
        """3단계: 차량번호 입력"""
        print("\n📍 3단계: 차량번호 입력")
        
        test_car_number = "1111"  # 테스트용 차량번호
        
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
                
                print(f"   ❌ 차량번호 '{search_number}'에 대한 검색 결과가 없습니다")
                
                # 텔레그램 알림 전송
                await self._send_vehicle_not_found_notification(search_number)
                await self._save_screenshot("step5_no_result")
                return False  # 검색 실패시 테스트 중단
            
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
    
    async def _step_6_apply_coupon(self):
        """6단계: 쿠폰 적용 (할인 로직에 따른 적절한 쿠폰 조합)"""
        print("\n📍 6단계: 쿠폰 적용 (할인 로직 기반)")
        
        try:
            # 2초 대기 후 현재 상태 스크린샷
            await self.page.wait_for_timeout(2000)
            await self._save_screenshot("step6_before_coupon")
            
            # 1. 현재 적용된 쿠폰 파싱 (A, B 매장과 동일한 방식)
            # 차량 선택 후 할인 내역이 로드될 때까지 대기
            await self.page.wait_for_timeout(3000)
            my_history, total_history = await self._parse_current_applied_coupons()
            
            # 2. 현재 쿠폰을 고려한 필요 쿠폰 계산
            required_coupons = self._calculate_required_coupons(my_history, total_history)
            
            print(f"   📊 필요 쿠폰 계산 결과:")
            for coupon_type, count in required_coupons.items():
                if count > 0:
                    coupon_config = self.config['coupons'].get(coupon_type, {})
                    coupon_name = coupon_config.get('name', coupon_type)
                    print(f"     - {coupon_name}: {count}개")
            
            # 모든 쿠폰이 0개인지 확인 (추가 할인이 불필요한 경우)
            total_required_coupons = sum(required_coupons.values())
            if total_required_coupons == 0:
                print(f"   ✅ 목표 할인 시간 이미 달성 - 추가 쿠폰 적용 불필요")
                return True
            
            # C 매장 쿠폰 매핑 (업데이트된 키 사용)
            coupon_mapping = {
                "FREE_2HOUR": [
                    "a:has-text('2시간 무료할인권')",
                    "a:has-text('무료 2시간')",
                    "a:has-text('무료할인권')",
                    "a:has-text('무료')",
                    "a[href*='discountticket'][href*='247']",
                    "a[href*='javascript:insert_discount'][href*='free']"
                ],
                "PAID_1HOUR": [
                    "a:has-text('1시간 유료할인권')",
                    "a:has-text('유료할인권')", 
                    "a:has-text('1시간')",
                    "a:has-text('유료')",
                    "a[href*='discountticket'][href*='246']",
                    "a[href*='discountticket(328304,246)']",
                    "a[href*='javascript:insert_discount'][href*='paid']"
                ]
            }
            
            # 필요한 쿠폰들을 순서대로 적용
            applied_coupons = []
            
            for coupon_type, needed_count in required_coupons.items():
                if needed_count <= 0:
                    continue
                    
                print(f"\n   🎯 {coupon_type} 쿠폰 {needed_count}개 적용 시도...")
                
                # 해당 쿠폰 타입의 셀렉터들 시도
                selectors = coupon_mapping.get(coupon_type, [])
                
                for i in range(needed_count):
                    coupon_found = False
                    
                    for selector in selectors:
                        try:
                            print(f"     🎯 셀렉터 시도: {selector}")
                            coupon_elements = await self.page.locator(selector).all()
                            print(f"     📊 발견된 요소 수: {len(coupon_elements)}개")
                            
                            for idx, element in enumerate(coupon_elements):
                                if await element.count() > 0:
                                    try:
                                        is_visible = await element.is_visible()
                                        coupon_text = await element.inner_text()
                                        href = await element.get_attribute('href')
                                        
                                        print(f"     🎫 요소 {idx+1}: '{coupon_text}' (visible: {is_visible}, href: {href})")
                                        
                                        if is_visible and coupon_text.strip():
                                            print(f"     ✅ 쿠폰 클릭 시도: {coupon_text}")
                                            await element.click()
                                            applied_coupons.append(f"{coupon_text}")
                                            
                                            # 쿠폰 적용 후 팝업 처리
                                            await self._handle_coupon_popup()
                                            
                                            # 간격 대기
                                            await self.page.wait_for_timeout(2000)
                                            
                                            print(f"     ✅ 쿠폰 적용 완료: {coupon_text}")
                                            coupon_found = True
                                            break
                                    except Exception as inner_e:
                                        print(f"     ⚠️ 요소 처리 실패: {str(inner_e)}")
                                        continue
                                    
                            if coupon_found:
                                break
                                
                        except Exception as e:
                            print(f"     ⚠️ 셀렉터 시도 실패 ({selector}): {str(e)}")
                            continue
                    
                    if not coupon_found:
                        print(f"     ⚠️  {coupon_type} 쿠폰을 찾을 수 없어 건너뛰")
                        break
            
            if not applied_coupons:
                print("   ❌ 필요한 쿠폰을 찾을 수 없음 - 페이지에서 사용 가능한 모든 쿠폰 확인")
                await self._save_screenshot("step6_no_coupon_found")
                
                # 페이지에서 사용 가능한 모든 쿠폰 링크 확인
                try:
                    all_links = await self.page.locator('a').all()
                    print(f"   🔍 페이지 내 총 링크 수: {len(all_links)}개")
                    
                    coupon_links = []
                    for link in all_links:
                        try:
                            href = await link.get_attribute('href')
                            text = await link.inner_text()
                            # ✅ C 매장 쿠폰 링크 판별 규칙: JavaScript 함수 호출만 쿠폰으로 인식
                            if href and href.startswith('javascript:insert_discount'):
                                coupon_links.append((text.strip(), href))
                                print(f"   🎫 쿠폰 링크 발견: '{text.strip()}' - {href}")
                        except:
                            continue
                    
                    # 사용 가능한 쿠폰이 있으면 첫 번째 것 사용
                    if coupon_links:
                        first_coupon_text, first_coupon_href = coupon_links[0]
                        print(f"   🎯 첫 번째 쿠폰 사용: {first_coupon_text}")
                        
                        coupon_element = self.page.locator(f'a[href="{first_coupon_href}"]').first
                        if await coupon_element.count() > 0:
                            await coupon_element.click()
                            applied_coupons.append(first_coupon_text)
                            await self._handle_coupon_popup()
                            await self.page.wait_for_timeout(2000)
                            print(f"   ✅ 쿠폰 적용 완료: {first_coupon_text}")
                    else:
                        print("   ⚠️ 사용 가능한 쿠폰이 없습니다")
                        return False
                        
                except Exception as e:
                    print(f"   ⚠️ 쿠폰 링크 분석 실패: {str(e)}")
                    return False
            
            print(f"\n   ✅ 쿠폰 적용 완료 - 적용된 쿠폰: {', '.join(applied_coupons)}")
            await self._save_screenshot("step6_coupon_applied_final")
            
            return True
            
        except Exception as e:
            print(f"   ❌ 쿠폰 적용 실패: {str(e)}")
            await self._save_screenshot("step6_coupon_failed")
            return False
        
        finally:
            # 최종 상태 확인 및 스크린샷
            try:
                await self.page.wait_for_timeout(2000)
                
                # 최종 할인 내역 다시 파싱하여 검증
                print("   🔍 최종 할인 내역 검증...")
                final_my_history, final_total_history = await self._parse_current_applied_coupons()
                
                if final_total_history:
                    total_applied_minutes = 0
                    for coupon_key, count in final_total_history.items():
                        if coupon_key == "FREE_2HOUR":
                            total_applied_minutes += count * 120
                        elif coupon_key == "PAID_1HOUR":
                            total_applied_minutes += count * 60
                    
                    target_minutes = 180 if self.is_weekday else 120
                    print(f"   📊 최종 검증 결과:")
                    print(f"     - 목표 시간: {target_minutes}분")
                    print(f"     - 적용된 총 할인: {total_applied_minutes}분")
                    print(f"     - 목표 달성: {'✅' if total_applied_minutes >= target_minutes else '❌'}")
                
            except Exception as verification_error:
                print(f"   ⚠️ 최종 검증 실패: {str(verification_error)}")
            
            await self._save_screenshot("step6_final_verification")
    
    async def _handle_coupon_popup(self):
        """쿠폰 적용 후 나타나는 팝업의 '닫기' 버튼 처리"""
        try:
            # 팝업 로딩 대기
            await self.page.wait_for_timeout(500)
            
            # 스크린샷에서 확인된 닫기 버튼 셀렉터들
            close_selectors = [
                # 스크린샷에서 확인된 정확한 셀렉터
                "#modalclose",
                "a[href='#close-modal']",
                ".close-modal",
                "a.btn.btn-active[href*='modal:close']",
                # 일반적인 닫기 버튼 셀렉터들
                "button:has-text('닫기')",
                "a:has-text('닫기')",
                "button:has-text('Close')",
                "a:has-text('Close')",
                ".modal-close",
                ".popup-close",
                "[data-dismiss='modal']",
                ".btn-close"
            ]
            
            popup_closed = False
            
            for selector in close_selectors:
                try:
                    close_button = self.page.locator(selector).first
                    if await close_button.count() > 0 and await close_button.is_visible():
                        print(f"     🔘 팝업 닫기 버튼 발견: {selector}")
                        await close_button.click()
                        print(f"     ✅ 팝업 닫기 버튼 클릭 완료")
                        
                        # 팝업이 닫힐 때까지 대기
                        await self.page.wait_for_timeout(800)
                        popup_closed = True
                        break
                        
                except Exception as e:
                    print(f"     ⚠️  닫기 버튼 클릭 시도 실패 ({selector}): {str(e)}")
                    continue
            
            if not popup_closed:
                print("     ⚠️  닫기 버튼을 찾을 수 없어 ESC 키로 팝업 닫기 시도")
                await self.page.keyboard.press('Escape')
                await self.page.wait_for_timeout(500)
                
        except Exception as e:
            print(f"     ⚠️  팝업 처리 중 오류: {str(e)}")
            # 팝업 처리 실패해도 계속 진행
    

    
    async def _send_vehicle_not_found_notification(self, vehicle_number):
        """차량 검색 실패 시 텔레그램 알림 전송"""
        try:
            if self.notification_service:
                error_context = ErrorContext(
                    store_id="C",
                    vehicle_number=vehicle_number,
                    error_step="차량검색",
                    error_message="검색된 차량이 없습니다",
                    error_time=datetime.now()
                )
                
                success = await self.notification_service.send_error_notification(error_context)
                if success:
                    print(f"   ✅ 텔레그램 알림 전송 성공: 차량번호 {vehicle_number} 검색 실패")
                else:
                    print(f"   ❌ 텔레그램 알림 전송 실패")
            else:
                print(f"   ⚠️ 텔레그램 알림 서비스가 설정되지 않음")
                
        except Exception as e:
            print(f"   ❌ 텔레그램 알림 전송 중 오류: {str(e)}")
    
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
        
        print("\n🧹 브라우저 자동 종료 중...")
        
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류: {str(e)}")
    finally:
        await test.cleanup()

if __name__ == "__main__":
    asyncio.run(main())