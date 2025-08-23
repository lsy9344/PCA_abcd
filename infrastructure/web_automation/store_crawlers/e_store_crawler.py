"""
E 매장 크롤러 - B매장과 동일한 구조 및 로직
"""
import asyncio
import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from playwright.async_api import Page, Browser, Playwright, async_playwright

from infrastructure.web_automation.base_crawler import BaseCrawler
from core.domain.repositories.store_repository import StoreRepository
from core.domain.models.vehicle import Vehicle
from core.domain.models.coupon import CouponHistory, CouponApplication
from utils.optimized_logger import OptimizedLogger, ErrorCode


class EStoreCrawler(BaseCrawler, StoreRepository):
    """E 매장 전용 크롤러 - B매장과 동일한 구조 및 로직"""
    
    def __init__(self, store_config: Any, playwright_config: Dict[str, Any], structured_logger: Any, notification_service: Optional[Any] = None):
        super().__init__(store_config, playwright_config, structured_logger, notification_service)
        self.store_id = "E"
        self.user_id = store_config.login_username
        self.logger = OptimizedLogger("e_store_crawler", "E")
    
    async def login(self, vehicle: Optional[Vehicle] = None) -> bool:
        """E 매장 로그인 및 팝업 처리"""
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
            
            # [수정] 로그인 성공의 핵심 지표인 '차량번호' 입력란이 나타날 때까지 명시적으로 기다립니다.
            # 이렇게 하면 페이지가 다음 작업을 위해 완전히 준비되었음을 보장할 수 있습니다.
            await self.page.get_by_role('textbox', name='차량번호').wait_for(state='visible', timeout=15000)
            
            self.logger.log_info("[성공] E 매장 로그인 및 차량 검색 페이지 로드 완료")
            
            # 팝업 처리 로직은 로그인 직후 바로 실행합니다.
            await self._handle_popups(self.page)
            
            # [수정] 체크박스 확인 로직은 이 함수의 책임이 아니므로 search_vehicle 함수로 이동했습니다.
            return True
            
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_AUTH, "로그인", f"로그인 또는 페이지 로드 실패: {str(e)}")
            return False

    async def search_vehicle(self, vehicle) -> bool:
        """차량 검색 (체크박스 확인 및 입차일 설정 로직 포함)"""
        try:
            # 문자열인 경우 Vehicle 객체로 변환
            if isinstance(vehicle, str):
                from core.domain.models.vehicle import Vehicle
                vehicle = Vehicle(number=vehicle)
            
            # [수정] 차량 검색을 시작하기 전에, 검색 기능의 일부인 체크박스 상태를 먼저 확인합니다.
            await self._ensure_search_state_checkbox(self.page)


            car_number = vehicle.number
            
            car_input = self.page.get_by_role('textbox', name='차량번호')
            await car_input.fill(car_number)
            self.logger.log_info(f"[성공] 차량번호 입력 완료: {car_number}")
            
            search_button = self.page.get_by_role('button', name='검색')
            if await search_button.count() == 0:
                raise Exception("검색 버튼을 찾을 수 없음")
            
            await search_button.click()
            self.logger.log_info(f"[성공] 검색 버튼 클릭 완료")
            await self.page.wait_for_timeout(2000)
            
            
            # 공통 차량 검색 실패 감지 로직 사용
            if await self.check_no_vehicle_found(self.page, car_number):
                self.logger.log_error(ErrorCode.NO_VEHICLE, "차량검색", f"차량번호 {car_number} 검색 결과 없음")
                return False
            
            # 검색 성공 (팝업이 없으면 성공으로 간주)
            self.logger.log_info(f"[성공] 차량번호 '{car_number}' 검색 성공")
            return True
            
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_SEARCH, "차량검색", str(e))
            return False

    async def get_coupon_history(self, vehicle) -> CouponHistory:
        """쿠폰 이력 조회 - E 매장 통합 로직 사용"""
        try:
            # 문자열인 경우 Vehicle 객체로 변환
            if isinstance(vehicle, str):
                from core.domain.models.vehicle import Vehicle
                vehicle = Vehicle(number=vehicle)
            
            # 통합 로직을 사용하여 현재 적용된 쿠폰 파싱
            my_history, total_history = await self._parse_current_applied_coupons()
            
            # 사용 가능한 쿠폰 정보 (기존 로직 유지)
            discount_info = {}
            discount_info['(무료) 1시간할인'] = {'car': 999, 'total': 999}
            
            remaining_amount_text = await self._check_remaining_amount_on_current_page(self.page)
            if remaining_amount_text:
                self._parse_remaining_amount(remaining_amount_text, discount_info)
            else:
                self.logger.log_info("[정보] 현재 페이지에서 남은잔여량 정보를 찾을 수 없음")
                paid_coupon_name = "(유료) 1시간할인"
                discount_info[paid_coupon_name] = {'car': 0, 'total': 0}
            
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
        """쿠폰 적용 - E 매장 전용 구현"""
        try:
            coupons_to_apply = {app.coupon_name: app.count for app in applications}
            self.logger.log_info(f"[쿠폰] E 매장 쿠폰 적용 시작: {coupons_to_apply}")
            
            total_applied = 0
            for coupon_name, count in coupons_to_apply.items():
                if count > 0:
                    # 쿠폰 이름을 통합 키로 매핑
                    coupon_type = None
                    if '무료' in coupon_name or 'FREE_COUPON' in coupon_name or 'FREE_1HOUR' in coupon_name:
                        coupon_type = 'FREE_1HOUR'
                    elif '유료' in coupon_name or 'PAID_COUPON' in coupon_name or 'PAID_1HOUR' in coupon_name:
                        coupon_type = 'PAID_1HOUR'
                    
                    if coupon_type:
                        for i in range(count):
                            if await self._apply_single_coupon(self.page, coupon_type, i + 1):
                                total_applied += 1
                            else:
                                self.logger.log_error(ErrorCode.FAIL_APPLY, "쿠폰적용", f"{coupon_name} {i + 1}개 적용 실패")
                                return False
                    else:
                        self.logger.log_error(ErrorCode.FAIL_APPLY, "쿠폰적용", f"알 수 없는 쿠폰 타입: {coupon_name}")
                        return False
            
            if total_applied > 0:
                self.logger.log_info(f"[완료] E 쿠폰 적용 완료: 총 {total_applied}개")
                return True
            else:
                self.logger.log_info("[정보] 적용할 쿠폰이 없음")
                return True # 적용할 게 없어도 성공으로 간주
            
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_APPLY, "쿠폰적용", str(e))
            return False

    async def _parse_current_applied_coupons(self):
        """통합 쿠폰 파싱 로직 사용 - YAML 설정 파일 기반"""
        from shared.utils.common_coupon_calculator import CommonCouponCalculator
        import yaml
        from pathlib import Path
        
        # YAML 설정 파일에서 직접 로드
        config_path = Path("infrastructure/config/store_configs/e_store_config.yaml")
        with open(config_path, 'r', encoding='utf-8') as f:
            store_config = yaml.safe_load(f)
        
        # 쿠폰 설정 추출
        coupon_config = store_config['selectors']['coupons']
        
        return await CommonCouponCalculator.parse_applied_coupons(
            self.page,
            coupon_config["coupon_key_mapping"],
            coupon_config["discount_selectors"],
            has_my_history=True
        )

    async def _handle_popups(self, page: Page):
        """팝업 처리"""
        try:
            # 팝업이 나타날 때까지 짧게 기다림
            await page.locator('text=안내').wait_for(state='visible', timeout=2000)
            ok_button = page.locator('text=OK')
            if await ok_button.count() > 0:
                await ok_button.click()
                await page.wait_for_timeout(1000)
                self.logger.log_info("[성공] 안내 팝업 처리 완료")
        except Exception:
            # 팝업이 없으면 그냥 통과
            self.logger.log_info("[정보] 처리할 팝업이 없음")


    async def _ensure_search_state_checkbox(self, page: Page):
        """검색 상태 유지 체크박스 확인 및 활성화 (안정화 버전)"""
        checkbox_selector = '#checkSaveID'
        try:
            # 체크박스가 나타날 때까지 최대 5초간 기다립니다.
            await page.wait_for_selector(checkbox_selector, state='visible', timeout=5000)
            
            checkbox_element = page.locator(checkbox_selector)
            
            if not await checkbox_element.is_checked():
                await checkbox_element.check()
                self.logger.log_info("[성공] 검색 상태 유지 체크박스 활성화 완료")
            else:
                self.logger.log_info("[정보] 검색 상태 유지 체크박스 이미 활성화됨")
                
        except Exception as e:
            # 5초를 기다려도 체크박스를 찾지 못하면 경고를 남깁니다.
            self.logger.log_warning(f"[경고] 검색 상태 유지 체크박스를 시간 내에 찾지 못함 (ID: {checkbox_selector}): {str(e)}")



    async def send_low_coupon_notification(self, coupon_count: int, remaining_amount: int) -> None:
        """쿠폰 부족 텔레그램 알림"""
        if self.notification_service:
            message = f"E 매장 보유 쿠폰 충전 필요 알림\n\n현재 쿠폰: {coupon_count}개\n남은 금액: {remaining_amount:,}원"
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
        """남은잔여량 텍스트에서 쿠폰 수량 계산 - E매장은 1시간 단위"""
        try:
            amount_match = re.search(r'([\d,]+)\s*원', amount_text)
            if amount_match:
                amount = int(amount_match.group(1).replace(',', ''))
                # E매장은 1시간 쿠폰 가격을 가정 (B매장과 다를 수 있음)
                # 임시로 300원으로 설정하되, 실제 가격에 맞게 조정 필요
                paid_1hour_count = amount // 300  
                paid_coupon_name = "(유료) 1시간할인"
                discount_info[paid_coupon_name] = {'car': paid_1hour_count, 'total': paid_1hour_count}
                self.logger.log_info(f"[성공] 유료 1시간할인: {paid_1hour_count}개")
                if paid_1hour_count <= 50:
                    self.logger.log_warning(f"[경고] E 매장 유료 1시간할인 쿠폰 부족: {paid_1hour_count}개")
                    asyncio.create_task(self.send_low_coupon_notification(paid_1hour_count, amount))
            else:
                self.logger.log_warning(f"[경고] 남은잔여량 숫자 추출 실패: {amount_text}")
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_PARSE, "남은잔여량파싱", str(e))


    async def _apply_single_coupon(self, page: Page, coupon_type: str, sequence: int) -> bool:
        """단일 쿠폰 적용"""
        try:
            self.logger.log_info(f"[쿠폰] {coupon_type} 쿠폰 적용 시작 (순서: {sequence})")
            current_rows = await self._count_discount_rows(page)
            
            link_text = '(무료) 1시간할인' if coupon_type == 'FREE_1HOUR' else '(유료) 1시간할인'
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
        """쿠폰 적용 후 팝업 처리 (안정화 버전)"""
        try:
            # '알림' 팝업의 'OK' 버튼을 직접 기다립니다.
            ok_button = page.locator('.modal-buttons a:has-text("OK")')
            await ok_button.wait_for(state='visible', timeout=3000)
            await ok_button.click()
            self.logger.log_info("[성공] 쿠폰 적용 알림 팝업 처리 완료")
            return True
        except Exception:
            self.logger.log_warning("[경고] 알림 팝업을 찾지 못했지만 계속 진행")
            return True


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


    async def cleanup(self) -> None:
        """리소스 정리 - StoreRepository 인터페이스 구현"""
        await super().cleanup()