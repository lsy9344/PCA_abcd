"""
C 매장 크롤러 구현
"""
import asyncio
import re
from typing import Dict, List, Optional
from playwright.async_api import Page, TimeoutError

from infrastructure.web_automation.base_crawler import BaseCrawler
from core.domain.repositories.store_repository import StoreRepository
from core.domain.models.vehicle import Vehicle
from core.domain.models.coupon import CouponHistory, CouponApplication
from utils.optimized_logger import OptimizedLogger, ErrorCode


class CStoreCrawler(BaseCrawler, StoreRepository):
    """C 매장 전용 크롤러"""
    
    def __init__(self, store_config, playwright_config, structured_logger, notification_service=None):
        super().__init__(store_config, playwright_config, structured_logger)
        self.store_id = "C"
        self.user_id = store_config.login_username
        self.notification_service = notification_service
        self.logger = OptimizedLogger("c_store_crawler", "C")
    
    async def login(self, vehicle: Vehicle = None) -> bool:
        """C 매장 로그인"""
        try:
            await self._initialize_browser()
            
            await self.page.goto(self.store_config.website_url)
            await self.page.wait_for_load_state('networkidle')
            
            # 로그인 폼 입력
            await self.page.fill(self.store_config.selectors['login']['username_input'], 
                               self.store_config.login_username)
            await self.page.fill(self.store_config.selectors['login']['password_input'], 
                               self.store_config.login_password)
            await self.page.click(self.store_config.selectors['login']['login_button'])
            
            # 로그인 성공 확인 - 차량번호 입력란이 나타날 때까지 대기
            await self.page.wait_for_selector(
                self.store_config.selectors['login']['car_number_input'], 
                timeout=15000
            )
            
            self.logger.log_info("[성공] C 매장 로그인 및 메인 페이지 로드 완료")
            
            # 팝업 처리
            await self._handle_popups()
            
            return True
            
        except TimeoutError:
            self.logger.log_error(ErrorCode.FAIL_AUTH, "로그인", "차량번호 입력란이 나타나지 않음")
            return False
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_AUTH, "로그인", str(e))
            return False

    async def search_vehicle(self, vehicle: Vehicle) -> bool:
        """차량 검색 및 선택"""
        try:
            car_number = vehicle.number
            
            # 차량번호 입력
            car_input_selector = self.store_config.selectors['search']['car_number_input']
            await self.page.fill(car_input_selector, car_number)
            self.logger.log_info(f"[진행] 차량번호 입력 완료: {car_number}")
            
            # 검색 버튼 클릭
            if not await self._click_search_button():
                return False
            
            # 검색 결과 로딩 대기
            await self.page.wait_for_timeout(3000)
            
            # 검색 결과 없음 확인
            no_result_selector = self.store_config.selectors['search']['no_result_message']
            no_result = self.page.locator(no_result_selector)
            if await no_result.count() > 0:
                await self._handle_no_result_popup()
                await self._send_no_vehicle_notification(car_number)
                self.logger.log_error(ErrorCode.NO_VEHICLE, "차량검색", f"차량번호 {car_number} 검색 결과 없음")
                return False
            
            # 검색된 차량을 테이블에서 클릭
            if not await self._select_vehicle_from_table(car_number):
                self.logger.log_error(ErrorCode.FAIL_SEARCH, "차량선택", f"테이블에서 차량번호 {car_number} 선택 실패")
                return False
            
            self.logger.log_info(f"[성공] 차량번호 '{car_number}' 검색 및 선택 완료")
            return True
            
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_SEARCH, "차량검색", str(e))
            return False

    async def get_coupon_history(self, vehicle: Vehicle) -> CouponHistory:
        """쿠폰 이력 조회"""
        try:
            my_history = {}
            total_history = {}
            available_coupons = {}
            
            # 기본 쿠폰 정보 설정 (실제 구현 시 페이지에서 파싱)
            coupon_configs = self.store_config.coupons
            for coupon_key, coupon_info in coupon_configs.items():
                available_coupons[coupon_info['name']] = {'car': 0, 'total': 0}
            
            # 쿠폰 리스트 파싱
            await self._parse_available_coupons(available_coupons)
            
            # 사용 이력 파싱
            await self._parse_coupon_history(my_history, total_history)
            
            return CouponHistory(
                store_id=self.store_id,
                vehicle_id=vehicle.number,
                my_history=my_history,
                total_history=total_history,
                available_coupons=available_coupons
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
        """쿠폰 적용"""
        try:
            coupons_to_apply = {app.coupon_name: app.count for app in applications}
            self.logger.log_info(f"[쿠폰] C 매장 쿠폰 적용 시작: {coupons_to_apply}")
            
            total_applied = 0
            for coupon_name, count in coupons_to_apply.items():
                if count > 0:
                    for i in range(count):
                        if await self._apply_single_coupon(coupon_name, i + 1):
                            total_applied += 1
                        else:
                            self.logger.log_error(ErrorCode.FAIL_APPLY, "쿠폰적용", 
                                                f"{coupon_name} {i + 1}개 적용 실패")
                            return False
            
            if total_applied > 0:
                self.logger.log_info(f"[완료] C 쿠폰 적용 완료: 총 {total_applied}개")
                return True
            else:
                self.logger.log_info("[정보] 적용할 쿠폰이 없음")
                return True
            
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_APPLY, "쿠폰적용", str(e))
            return False

    async def _handle_popups(self):
        """팝업 처리"""
        try:
            # 공통 팝업 처리 로직 (OK, 확인, 닫기 버튼)
            popup_selectors = [
                self.store_config.selectors['popups']['ok_button'],
                self.store_config.selectors['popups']['close_button'],
                'text=확인', 'text=OK', 'text=닫기'
            ]
            
            for selector in popup_selectors:
                try:
                    popup_button = self.page.locator(selector)
                    if await popup_button.count() > 0:
                        await popup_button.first.click()
                        await self.page.wait_for_timeout(1000)
                        self.logger.log_info(f"[성공] 팝업 처리 완료: {selector}")
                        break
                except Exception:
                    continue
                    
        except Exception as e:
            self.logger.log_info(f"[정보] 처리할 팝업이 없음: {str(e)}")

    async def _handle_no_result_popup(self):
        """검색 결과 없음 팝업 처리"""
        try:
            close_buttons = ['text=OK', 'text=확인', '.popup-ok', '.close-btn']
            for selector in close_buttons:
                close_button = self.page.locator(selector)
                if await close_button.count() > 0:
                    await close_button.first.click()
                    await self.page.wait_for_timeout(1000)
                    self.logger.log_info("[성공] 검색 결과 없음 팝업 닫기 완료")
                    break
        except Exception as e:
            self.logger.log_warning(f"[경고] 팝업 닫기 실패: {str(e)}")

    async def _send_no_vehicle_notification(self, car_number: str):
        """차량 검색 결과 없음 알림"""
        self.logger.log_warning(f"[경고] C 매장에서 차량번호 '{car_number}' 검색 결과가 없습니다.")

    async def _send_low_coupon_notification(self, coupon_name: str, coupon_count: int):
        """쿠폰 부족 텔레그램 알림"""
        if self.notification_service:
            message = f"C 매장 보유 쿠폰 충전 필요 알림\n\n쿠폰 종류: {coupon_name}\n현재 쿠폰: {coupon_count}개\n권장 최소량: 50개"
            await self.notification_service.send_success_notification(message=message, store_id=self.store_id)
            self.logger.log_info("[성공] 쿠폰 부족 텔레그램 알림 전송 완료")
        else:
            self.logger.log_warning("[경고] 텔레그램 알림 서비스가 설정되지 않음")

    async def _parse_available_coupons(self, available_coupons: Dict):
        """보유 쿠폰 파싱"""
        try:
            coupon_list_selector = self.store_config.selectors['coupons']['coupon_list']
            coupon_rows_selector = self.store_config.selectors['coupons']['coupon_rows']
            
            # 쿠폰 리스트가 있는지 확인
            if await self.page.locator(coupon_list_selector).count() > 0:
                rows = await self.page.locator(coupon_rows_selector).all()
                for row in rows:
                    try:
                        text = await row.inner_text()
                        # 쿠폰 이름과 수량 파싱 (사이트별 맞춤 구현 필요)
                        for coupon_name in available_coupons.keys():
                            if coupon_name in text:
                                # 수량 추출 로직 (예: "쿠폰명 10개" 형태)
                                count_match = re.search(r'(\d+)', text)
                                if count_match:
                                    count = int(count_match.group(1))
                                    available_coupons[coupon_name] = {'car': count, 'total': count}
                                    
                                    # 쿠폰 부족 알림
                                    if count <= 50 and count > 0:
                                        self.logger.log_warning(f"[경고] C 매장 {coupon_name} 쿠폰 부족: {count}개")
                                        asyncio.create_task(self._send_low_coupon_notification(coupon_name, count))
                                break
                    except Exception:
                        continue
                        
        except Exception as e:
            self.logger.log_warning(f"[경고] 쿠폰 리스트 파싱 실패: {str(e)}")

    async def _parse_coupon_history(self, my_history: Dict, total_history: Dict):
        """쿠폰 사용 이력 파싱"""
        try:
            history_selector = self.store_config.selectors['coupons']['discount_history']
            
            if await self.page.locator(history_selector).count() > 0:
                rows = await self.page.locator(f"{history_selector} tr").all()
                for row in rows:
                    try:
                        cells = await row.locator('td').all_text_contents()
                        if len(cells) >= 3:
                            # 사용자, 쿠폰타입, 사용일시 등 파싱
                            user_info = cells[0].strip()
                            coupon_type = cells[1].strip()
                            
                            # 쿠폰 타입 매핑
                            mapped_type = self._map_coupon_type(coupon_type)
                            if mapped_type:
                                total_history[mapped_type] = total_history.get(mapped_type, 0) + 1
                                
                                # 현재 사용자의 이력인지 확인
                                if self.user_id in user_info:
                                    my_history[mapped_type] = my_history.get(mapped_type, 0) + 1
                                    
                    except Exception:
                        continue
                        
        except Exception as e:
            self.logger.log_warning(f"[경고] 쿠폰 이력 파싱 실패: {str(e)}")

    def _map_coupon_type(self, coupon_text: str) -> Optional[str]:
        """쿠폰 텍스트를 표준 타입으로 매핑"""
        if "무료" in coupon_text and "1시간" in coupon_text:
            return "FREE_1HOUR"
        elif "유료" in coupon_text and "30분" in coupon_text:
            return "PAID_30MIN"
        elif "유료" in coupon_text and "1시간" in coupon_text:
            return "PAID_1HOUR"
        return None

    async def _apply_single_coupon(self, coupon_name: str, sequence: int) -> bool:
        """단일 쿠폰 적용"""
        try:
            self.logger.log_info(f"[쿠폰] {coupon_name} 쿠폰 적용 시작 (순서: {sequence})")
            
            # 쿠폰 목록에서 해당 쿠폰 찾아서 적용 버튼 클릭
            coupon_rows = await self.page.locator(self.store_config.selectors['coupons']['coupon_rows']).all()
            for row in coupon_rows:
                text = await row.inner_text()
                if coupon_name in text:
                    apply_button = row.locator(self.store_config.selectors['coupons']['apply_button'])
                    if await apply_button.count() > 0:
                        await apply_button.first.click()
                        await self.page.wait_for_timeout(1000)
                        
                        # 적용 확인 팝업 처리
                        await self._handle_apply_confirmation()
                        
                        self.logger.log_info(f"[성공] {coupon_name} 적용 완료")
                        return True
            
            self.logger.log_error(ErrorCode.FAIL_APPLY, "쿠폰적용", f"{coupon_name} 적용 버튼을 찾을 수 없음")
            return False
            
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_APPLY, "쿠폰적용", f"{coupon_name} 적용 중 오류: {str(e)}")
            return False

    async def _handle_apply_confirmation(self):
        """쿠폰 적용 확인 팝업 처리"""
        try:
            confirmation_selectors = ['text=확인', 'text=OK', '.confirm-btn', '.popup-ok']
            for selector in confirmation_selectors:
                button = self.page.locator(selector)
                if await button.count() > 0:
                    await button.first.click()
                    await self.page.wait_for_timeout(500)
                    self.logger.log_info("[성공] 쿠폰 적용 확인 팝업 처리 완료")
                    break
        except Exception as e:
            self.logger.log_warning(f"[경고] 확인 팝업 처리 실패: {str(e)}")

    async def _click_search_button(self) -> bool:
        """검색 버튼 클릭 (여러 셀렉터 시도)"""
        try:
            search_selectors = [
                self.store_config.selectors['search']['search_button'],
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
                        self.logger.log_info(f"[성공] 검색 버튼 클릭: {selector}")
                        return True
                except Exception:
                    continue
            
            self.logger.log_error(ErrorCode.FAIL_SEARCH, "버튼클릭", "검색 버튼을 찾을 수 없음")
            return False
            
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_SEARCH, "버튼클릭", str(e))
            return False

    async def _select_vehicle_from_table(self, car_number: str) -> bool:
        """검색 결과 테이블에서 차량 선택"""
        try:
            # 스크린샷 기반으로 확인된 테이블 셀렉터들 - UI 테스트로 검증됨
            table_selectors = [
                "#tableID",  # 스크린샷에서 확인된 실제 테이블 ID (camelCase) - UI 테스트로 검증
                self.store_config.selectors['search']['search_result_table'],  # 설정파일의 테이블 셀렉터
                "#tableid",  # 백업용 (소문자)
                "table",
                ".table-box",
                "[id*='table']"
            ]
            
            for table_selector in table_selectors:
                try:
                    table = self.page.locator(table_selector)
                    if await table.count() > 0:
                        self.logger.log_info(f"[진행] 테이블 발견: {table_selector}")
                        
                        # 테이블의 모든 행 검사
                        rows = await table.locator('tr').all()
                        
                        for row in rows:
                            try:
                                row_text = await row.inner_text()
                                
                                if car_number in row_text:
                                    # 차량번호가 포함된 행에서 클릭 가능한 요소 찾기
                                    clickable_elements = [
                                        row.locator(f'td:has-text("{car_number}")'),
                                        row.locator('a'),
                                        row.locator('[onclick]'),
                                        row.locator('td').first
                                    ]
                                    
                                    for element in clickable_elements:
                                        if await element.count() > 0:
                                            await element.first.click()
                                            self.logger.log_info(f"[성공] 차량번호 '{car_number}' 클릭 완료")
                                            await self.page.wait_for_timeout(2000)
                                            return True
                                            
                            except Exception:
                                continue
                        
                        # 테이블은 찾았지만 차량번호가 없는 경우
                        self.logger.log_warning(f"[경고] 테이블에서 차량번호 '{car_number}'를 찾을 수 없음")
                        return False
                        
                except Exception:
                    continue
            
            # 모든 테이블 셀렉터에서 실패한 경우
            self.logger.log_error(ErrorCode.FAIL_SEARCH, "테이블검색", "검색 결과 테이블을 찾을 수 없음")
            await self._debug_page_state()
            return False
            
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_SEARCH, "차량선택", str(e))
            return False

    async def _debug_page_state(self):
        """디버깅을 위한 페이지 상태 출력"""
        try:
            self.logger.log_info(f"[디버그] 현재 URL: {self.page.url}")
            
            # 페이지의 모든 테이블 요소 확인
            tables = await self.page.locator('table').all()
            self.logger.log_info(f"[디버그] 페이지의 테이블 개수: {len(tables)}")
            
            # ID가 있는 요소들 확인
            elements_with_id = await self.page.evaluate("""
                () => {
                    const elements = document.querySelectorAll('[id]');
                    return Array.from(elements).slice(0, 20).map(el => el.id);
                }
            """)
            self.logger.log_info(f"[디버그] ID가 있는 요소들(상위 20개): {elements_with_id}")
            
        except Exception as e:
            self.logger.log_warning(f"[경고] 디버깅 정보 수집 실패: {str(e)}")

    async def cleanup(self) -> None:
        """리소스 정리"""
        await super().cleanup()