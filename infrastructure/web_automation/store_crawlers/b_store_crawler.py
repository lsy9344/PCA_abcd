"""
B 매장 크롤러 - 테스트용 날짜 설정 로직 제거된 최종 버전
"""
import asyncio
import re
import logging
from typing import Dict, List, Optional, Tuple
from playwright.async_api import Page, Browser, Playwright, async_playwright

from infrastructure.web_automation.base_crawler import BaseCrawler
from core.domain.models.vehicle import Vehicle
from core.domain.models.coupon import CouponHistory, CouponApplication
from utils.optimized_logger import OptimizedLogger, ErrorCode


class BStoreCrawler(BaseCrawler):
    """B 매장 전용 크롤러 - 테스트용 날짜 설정 로직 제거된 최종 버전"""
    
    def __init__(self, store_config, playwright_config, structured_logger, notification_service=None):
        super().__init__(store_config, playwright_config, structured_logger)
        self.store_id = "B"
        self.user_id = store_config.login_username
        self.notification_service = notification_service
        self.logger = OptimizedLogger("b_store_crawler", "B")
    
    async def login(self, vehicle: Vehicle = None) -> bool:
        """B 매장 로그인"""
        try:
            await self._initialize_browser()
            
            await self.page.goto(self.store_config.website_url)
            await self.page.wait_for_load_state('networkidle')
            
            username_input = self.page.get_by_role('textbox', name='ID')
            password_input = self.page.get_by_role('textbox', name='PASSWORD')
            login_button = self.page.get_by_role('button', name='Submit')
            
            await username_input.fill(self.store_config.login_username)
            await password_input.fill(self.store_config.login_password)
            await login_button.click()
            
            await self.page.wait_for_timeout(3000)
            
            success_indicator = self.page.locator('text=사용자')
            if await success_indicator.count() > 0:
                self.logger.log_info("[성공] B 매장 로그인 성공")
                
                await self._handle_popups(self.page)
                await self._ensure_search_state_checkbox(self.page)
                
                # ✅ 테스트용 날짜 설정 로직과 그 호출을 완전히 제거했습니다.
                
                return True
            else:
                self.logger.log_error(ErrorCode.FAIL_AUTH, "로그인", "성공 지표를 찾을 수 없음")
                return False
                
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_AUTH, "로그인", str(e))
            return False

    async def search_vehicle(self, vehicle: Vehicle) -> bool:
        """차량 검색"""
        try:
            car_number = vehicle.number
            
            car_input = self.page.get_by_role('textbox', name='차량번호')
            if await car_input.count() == 0:
                raise Exception("차량번호 입력란을 찾을 수 없음")
            
            await car_input.fill(car_number)
            
            search_button = self.page.get_by_role('button', name='검색')
            if await search_button.count() == 0:
                raise Exception("검색 버튼을 찾을 수 없음")
            
            await search_button.click()
            await self.page.wait_for_timeout(2000)
            
            no_result_patterns = [
                'text=검색 결과가 없습니다', 'text="검색 결과가 없습니다"',
                'text=검색된 차량이 없습니다', 'text="검색된 차량이 없습니다"'
            ]
            
            for pattern in no_result_patterns:
                no_result = self.page.locator(pattern)
                if await no_result.count() > 0:
                    self.logger.log_warning(f"[경고] 차량번호 '{car_number}' 검색 결과 없음 팝업 감지")
                    
                    close_buttons = ['text=OK', 'text="OK"', 'text=확인', 'text="확인"']
                    for close_button_selector in close_buttons:
                        close_button = self.page.locator(close_button_selector)
                        if await close_button.count() > 0:
                            await close_button.click()
                            await self.page.wait_for_timeout(1000)
                            self.logger.log_info("[성공] 검색 결과 없음 팝업 닫기 완료")
                            break
                    
                    await self._send_no_vehicle_notification(car_number)
                    self.logger.log_error(ErrorCode.NO_VEHICLE, "차량검색", f"차량번호 {car_number} 검색 결과 없음")
                    return False
            
            self.logger.log_info(f"[성공] 차량번호 '{car_number}' 검색 성공")
            return True
            
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_SEARCH, "차량검색", str(e))
            return False

    async def get_coupon_history(self, vehicle: Vehicle) -> CouponHistory:
        """쿠폰 이력 조회 - B 매장 전용 구현"""
        try:
            my_history = {}
            total_history = {}
            discount_info = {}
            
            discount_info['무료 1시간할인'] = {'car': 999, 'total': 999}
            
            remaining_amount_text = await self._check_remaining_amount_on_current_page(self.page)
            if remaining_amount_text:
                self._parse_remaining_amount(remaining_amount_text, discount_info)
            else:
                self.logger.log_info("[정보] 현재 페이지에서 남은잔여량 정보를 찾을 수 없음")
                paid_coupon_name = "유료 30분할인 (판매 : 300 )"
                discount_info[paid_coupon_name] = {'car': 0, 'total': 0}
            
            await self._analyze_discount_history(self.page, my_history, total_history)
            
            return CouponHistory(
                store_id=self.store_id,
                vehicle_id=vehicle.number,
                my_history=my_history,
                total_history=total_history,
                available_coupons=discount_info
            )
            
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_PARSE, "쿠폰조회", str(e))
            return CouponHistory(
                store_id=self.store_id,
                vehicle_id=vehicle.number,
                my_history={},
                total_history={},
                available_coupons={}
            )

    async def apply_coupons(self, applications: List[CouponApplication]) -> bool:
        """쿠폰 적용 - B 매장 전용 구현"""
        try:
            coupons_to_apply = {app.coupon_name: app.count for app in applications}
            self.logger.log_info(f"[쿠폰] B 매장 쿠폰 적용 시작: {coupons_to_apply}")
            
            total_applied = 0
            for coupon_name, count in coupons_to_apply.items():
                if count > 0:
                    coupon_type = 'FREE_1HOUR' if '무료' in coupon_name else 'PAID_30MIN'
                    for i in range(count):
                        if await self._apply_single_coupon(self.page, coupon_type, i + 1):
                            total_applied += 1
                        else:
                            self.logger.log_error(ErrorCode.FAIL_APPLY, "쿠폰적용", f"{coupon_name} {i + 1}개 적용 실패")
                            return False
            
            if total_applied > 0:
                self.logger.log_info(f"[완료] B 쿠폰 적용 완료: 총 {total_applied}개")
                return True
            else:
                self.logger.log_info("[정보] 적용할 쿠폰이 없음")
                return True # 적용할 게 없어도 성공으로 간주
            
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_APPLY, "쿠폰적용", str(e))
            return False

    async def _handle_popups(self, page: Page):
        """팝업 처리"""
        try:
            notice_popup = page.locator('text=안내')
            if await notice_popup.count() > 0:
                ok_button = page.locator('text=OK')
                if await ok_button.count() > 0:
                    await ok_button.click()
                    await page.wait_for_timeout(1000)
                    self.logger.log_info("[성공] 안내 팝업 처리 완료")
        except Exception as e:
            self.logger.log_warning(f"[경고] 팝업 처리 중 오류 (무시하고 계속): {str(e)}")

    async def _ensure_search_state_checkbox(self, page: Page):
        """
        검색 상태 유지 체크박스 확인 및 활성화 (타이밍 문제 해결을 위해 명시적 대기 추가)
        """
        checkbox_selector = '#checkSaveId'
        try:
            # [수정] 체크박스가 나타날 때까지 최대 5초간 기다립니다.
            await page.wait_for_selector(checkbox_selector, state='visible', timeout=5000)
            
            checkbox_element = page.locator(checkbox_selector)
            
            if not await checkbox_element.is_checked():
                # 체크되어 있지 않으면 체크합니다.
                await checkbox_element.check()
                self.logger.log_info("[성공] 검색 상태 유지 체크박스 활성화 완료")
            else:
                self.logger.log_info("[정보] 검색 상태 유지 체크박스 이미 활성화됨")
                
        except Exception as e:
            # 5초를 기다려도 체크박스를 찾지 못하면 경고를 남깁니다.
            self.logger.log_warning(f"[경고] 검색 상태 유지 체크박스를 시간 내에 찾지 못함 (ID: {checkbox_selector}): {str(e)}")

    async def _send_no_vehicle_notification(self, car_number: str):
        """차량 검색 결과 없음 알림"""
        self.logger.log_warning(f"[경고] B 매장에서 차량번호 '{car_number}' 검색 결과가 없습니다.")

    async def _send_low_coupon_notification(self, coupon_count: int, remaining_amount: int):
        """쿠폰 부족 텔레그램 알림"""
        if self.notification_service:
            message = f"B 매장 보유 쿠폰 충전 필요 알림\n\n현재 쿠폰: {coupon_count}개\n남은 금액: {remaining_amount:,}원"
            await self.notification_service.send_success_notification(message=message, store_id=self.store_id)
            self.logger.log_info("[성공] 쿠폰 부족 텔레그램 알림 전송 완료")
        else:
            self.logger.log_warning("[경고] 텔레그램 알림 서비스가 설정되지 않음")

    async def _check_remaining_amount_on_current_page(self, page: Page) -> Optional[str]:
        """현재 페이지에서 남은잔여량 확인"""
        try:
            elements = page.locator('text=남은잔여량')
            if await elements.count() > 0:
                parent = elements.first.locator('..')
                text = await parent.text_content()
                if text and "원" in text:
                    return text
            return None
        except Exception:
            return None

    def _parse_remaining_amount(self, amount_text: str, discount_info: Dict):
        """남은잔여량 텍스트에서 쿠폰 수량 계산"""
        try:
            amount_match = re.search(r'([\d,]+)\s*원', amount_text)
            if amount_match:
                amount = int(amount_match.group(1).replace(',', ''))
                paid_30min_count = amount // 300
                paid_coupon_name = "유료 30분할인 (판매 : 300 )"
                discount_info[paid_coupon_name] = {'car': paid_30min_count, 'total': paid_30min_count}
                self.logger.log_info(f"[성공] 유료 30분할인: {paid_30min_count}개")
                if paid_30min_count <= 50:
                    self.logger.log_warning(f"[경고] B 매장 유료 30분할인 쿠폰 부족: {paid_30min_count}개")
                    asyncio.create_task(self._send_low_coupon_notification(paid_30min_count, amount))
            else:
                self.logger.log_warning(f"[경고] 남은잔여량 숫자 추출 실패: {amount_text}")
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_PARSE, "남은잔여량파싱", str(e))

    async def _analyze_discount_history(self, page: Page, my_history: Dict, total_history: Dict):
        """할인등록현황 테이블 분석"""
        try:
            data_rows = page.locator('tr.ev_dhx_skyblue, tr.odd_dhx_skyblue')
            for i in range(await data_rows.count()):
                row = data_rows.nth(i)
                cells = await row.locator('td').all_text_contents()
                if len(cells) >= 4:
                    await self._process_discount_row(cells, my_history, total_history)
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_PARSE, "할인내역분석", str(e))

    async def _process_discount_row(self, cell_contents: List[str], my_history: Dict, total_history: Dict):
        """할인 데이터 행 처리"""
        try:
            discount_value = cell_contents[1].strip()
            registrant = cell_contents[2].strip()
            coupon_type = self._extract_coupon_type(discount_value)
            if coupon_type:
                total_history[coupon_type] = total_history.get(coupon_type, 0) + 1
                registrant_id = registrant.split('(')[0].strip()
                if registrant_id == self.user_id:
                    my_history[coupon_type] = my_history.get(coupon_type, 0) + 1
        except Exception as e:
            self.logger.log_warning(f"[경고] 할인 행 처리 중 오류: {str(e)}")

    def _extract_coupon_type(self, discount_value: str) -> Optional[str]:
        """할인값에서 쿠폰 타입 추출"""
        if "무료 1시간할인" in discount_value: return "FREE_1HOUR"
        if "무료 30분할인" in discount_value: return "FREE_30MIN"
        if "유료 30분할인" in discount_value: return "PAID_30MIN"
        if "유료 1시간할인" in discount_value: return "PAID_1HOUR"
        self.logger.log_warning(f"[경고] 알 수 없는 할인 타입: {discount_value}")
        return None

    async def _apply_single_coupon(self, page: Page, coupon_type: str, sequence: int) -> bool:
        """단일 쿠폰 적용"""
        try:
            self.logger.log_info(f"[쿠폰] {coupon_type} 쿠폰 적용 시작 (순서: {sequence})")
            current_rows = await self._count_discount_rows(page)
            
            link_text = '무료 1시간할인' if coupon_type == 'FREE_1HOUR' else '유료 30분할인'
            discount_link = page.locator(f'a:has-text("{link_text}")')
            
            if await discount_link.count() > 0:
                await discount_link.first.click()
            else:
                self.logger.log_error(ErrorCode.FAIL_APPLY, "쿠폰적용", f"{link_text} 링크를 찾을 수 없음")
                return False
            
            await page.wait_for_timeout(500)
            if not await self._handle_apply_popups_without_navigation(page):
                return False
            
            if await self._wait_for_discount_table_update(page, current_rows):
                self.logger.log_info("[성공] 할인내역 테이블 업데이트 확인 완료")
                return True
            else:
                self.logger.log_warning("[경고] 할인내역 테이블 업데이트 확인 실패, 하지만 계속 진행")
                return True
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_APPLY, "쿠폰적용", f"{coupon_type} 적용 중 오류: {str(e)}")
            return False

    async def _handle_apply_popups_without_navigation(self, page: Page) -> bool:
        """쿠폰 적용 후 팝업 처리"""
        try:
            # 3초 동안 팝업이 나타나는지 반복 확인
            for _ in range(6): 
                popup_title = page.locator('h3:has-text("알림")')
                if await popup_title.count() > 0:
                    # ❗수정된 부분: 'button'을 'a'로 변경하여 <a> 태그를 찾도록 수정
                    ok_button = page.locator('.modal-buttons a:has-text("OK")')
                    
                    if await ok_button.count() > 0:
                        await ok_button.click()
                        self.logger.log_info("[성공] 쿠폰 적용 알림 팝업 처리 완료")
                        return True
                await page.wait_for_timeout(500)
                
            self.logger.log_warning("[경고] 알림 팝업을 찾지 못했지만 계속 진행")
            return True
            
        except Exception as e:
            self.logger.log_warning(f"[경고] 쿠폰 적용 팝업 처리 중 오류: {str(e)}")
            return False
        
    async def _count_discount_rows(self, page: Page) -> int:
        """현재 할인내역 테이블의 행 수 계산"""
        try:
            return await page.locator('tr.ev_dhx_skyblue, tr.odd_dhx_skyblue').count()
        except Exception:
            return 0

    async def _wait_for_discount_table_update(self, page: Page, previous_count: int) -> bool:
        """할인내역 테이블 업데이트 대기"""
        for _ in range(10): # 5초 대기
            await page.wait_for_timeout(500)
            if await self._count_discount_rows(page) > previous_count:
                return True
        return False
