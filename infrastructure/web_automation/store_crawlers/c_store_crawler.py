"""
C 매장 크롤러 구현
"""
import asyncio
import re
from typing import Dict, List, Optional, Any
from playwright.async_api import Page, TimeoutError

from infrastructure.web_automation.base_crawler import BaseCrawler
from core.domain.repositories.store_repository import StoreRepository
from core.domain.models.vehicle import Vehicle
from core.domain.models.coupon import CouponHistory, CouponApplication
from utils.optimized_logger import OptimizedLogger, ErrorCode


class CStoreCrawler(BaseCrawler, StoreRepository):
    """C 매장 전용 크롤러"""
    
    def __init__(self, store_config: Any, playwright_config: Dict[str, Any], structured_logger: Any, notification_service: Optional[Any] = None):
        super().__init__(store_config, playwright_config, structured_logger, notification_service)
        self.store_id = "C"
        
        # ConfigManager를 통한 통합 설정 사용 (92번 지침 준수)
        # store_config는 이미 ConfigManager에서 완전한 객체로 전달됨
        
        # 설정 파일에서 로그인 정보 로드 (다른 매장과 동일)
        self.username = self.store_config.login_username
        self.password = self.store_config.login_password
        
        self.user_id = self.username  # 기존 호환성 유지
        self.logger = OptimizedLogger("c_store_crawler", "C")
    

    async def login(self, vehicle: Optional[Vehicle] = None) -> bool:
        """C 매장 로그인"""
        try:
            await self._initialize_browser()
            
            await self.page.goto(self.store_config.website_url)
            await self.page.wait_for_load_state('networkidle')
            
            # 로그인 폼 입력 (환경 변수 사용)
            await self.page.fill(self.store_config.selectors['login']['username_input'], 
                               self.username)
            await self.page.fill(self.store_config.selectors['login']['password_input'], 
                               self.password)
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
            self.logger.log_info(f"[성공] 차량번호 입력 완료: {car_number}")
            
            # 검색 버튼 클릭
            if not await self._click_search_button():
                return False
            
            # 검색 결과 로딩 대기
            await self.page.wait_for_timeout(3000)
            
            # 검색 결과 없음 팝업 확인 (UI 테스트와 동일한 로직)
            no_result_message = 'text=검색된 차량이 없습니다'
            if await self.page.locator(no_result_message).count() > 0:
                # 텔레그램 알림 전송
                await self._send_no_vehicle_notification(car_number)
                self.logger.log_error(ErrorCode.NO_VEHICLE, "차량검색", f"차량번호 {car_number} 검색 결과 없음")
                # 팝업 닫기
                await self._handle_no_result_popup()
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
            
            # 페이지 안전성 검사
            if not await self._safe_page_check():
                self.logger.log_warning("페이지 상태 불안정 - 빈 이력 반환")
                return self._empty_coupon_history(vehicle.number)
            
            # 기본 쿠폰 정보 설정 (YAML 파일에서 직접 로드)
            try:
                # C 매장 설정 로드 (YAML 파일에서 직접)
                import yaml
                from pathlib import Path
                
                config_path = Path("infrastructure/config/store_configs/c_store_config.yaml")
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                coupon_configs = config.get('coupons', {})
                for coupon_key, coupon_info in coupon_configs.items():
                    # 기본값을 충분한 개수로 설정 (실제 파싱이 실패해도 쿠폰 적용 가능하도록)
                    available_coupons[coupon_info['name']] = {'car': 100, 'total': 100}
            except Exception as config_e:
                self.logger.log_error(ErrorCode.FAIL_PARSE, "쿠폰설정", f"쿠폰 설정 로드 실패: {str(config_e)}")
                raise
            
            # C 매장은 my_history가 없음 (설정 파일 기준)
            my_history = {}
            
            # 쿠폰 리스트 파싱
            try:
                await self._parse_available_coupons(available_coupons)
            except Exception as parse_e:
                self.logger.log_error(ErrorCode.FAIL_PARSE, "사용가능쿠폰", f"사용 가능 쿠폰 파싱 실패: {str(parse_e)}")
            
            # 사용 이력 파싱 (C 매장 전용 로직)
            try:
                await self._parse_coupon_history_c_store(total_history)
            except Exception as history_e:
                self.logger.log_error(ErrorCode.FAIL_PARSE, "쿠폰이력", f"쿠폰 이력 파싱 실패: {str(history_e)}")
            
            return CouponHistory(
                store_id=self.store_id,
                vehicle_id=vehicle.number,
                my_history=my_history,
                total_history=total_history,
                available_coupons=available_coupons
            )
            
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_PARSE, "쿠폰조회", str(e))
            return self._empty_coupon_history(vehicle.number)

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


    async def send_low_coupon_notification(self, coupon_name: str, coupon_count: int) -> None:
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
                                        asyncio.create_task(self.send_low_coupon_notification(coupon_name, count))
                                break
                    except Exception:
                        continue
                        
        except Exception as e:
            self.logger.log_warning(f"[경고] 쿠폰 리스트 파싱 실패: {str(e)}")


    def _map_coupon_type(self, coupon_text: str) -> Optional[str]:
        """쿠폰 텍스트를 표준 타입으로 매핑 - ConfigManager 기반 동적 매핑"""
        try:
            # ConfigManager에서 로드된 설정 사용 (92번 지침)
            for coupon_key, coupon_info in self.store_config.coupons.items():
                coupon_name = coupon_info['name']
                
                # 쿠폰 이름이 텍스트에 포함되는지 확인
                if coupon_name in coupon_text:
                    return coupon_key
                
                # 백업 매칭: 키워드 기반
                # FREE_2HOUR의 경우: "무료"와 "2시간" 키워드 포함
                if coupon_info['type'] == 'FREE' and "무료" in coupon_text:
                    # 시간 정보 매칭 (예: 120분 = 2시간)
                    duration_hours = coupon_info['duration_minutes'] // 60
                    if f"{duration_hours}시간" in coupon_text:
                        return coupon_key
                        
                # PAID_1HOUR의 경우: "유료"와 "1시간" 키워드 포함  
                elif coupon_info['type'] == 'PAID' and "유료" in coupon_text:
                    # 시간 정보 매칭
                    duration_hours = coupon_info['duration_minutes'] // 60
                    if f"{duration_hours}시간" in coupon_text:
                        return coupon_key
            
            # 매칭되지 않으면 None 반환
            return None
            
        except Exception as e:
            self.logger.log_warning(f"쿠폰 타입 매핑 오류: {str(e)}")
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
                        return True
                except Exception:
                    continue
            
            self.logger.log_error(ErrorCode.FAIL_SEARCH, "버튼클릭", "검색 버튼을 찾을 수 없음")
            return False
            
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_SEARCH, "버튼클릭", str(e))
            return False

    async def _select_vehicle_from_table(self, car_number: str) -> bool:
        """검색 결과 테이블에서 차량 선택 - UI 테스트와 동일한 로직"""
        try:
            # 테이블 찾기 및 차량 선택 - UI 테스트에서 검증된 셀렉터들 사용
            table_selectors = [
                "#tableID",  # UI 테스트에서 확인된 실제 테이블 ID (camelCase)
                "#tableid",
                "#searchResult", 
                "table",
                ".table-box"
            ]
            
            for table_selector in table_selectors:
                try:
                    table = self.page.locator(table_selector)
                    if await table.count() > 0:
                        # 테이블의 모든 행 검사 (UI 테스트와 동일)
                        rows = await table.locator('tbody tr').all()
                        if len(rows) == 0:
                            # tbody가 없는 경우 일반 tr 사용
                            rows = await table.locator('tr').all()
                        
                        for i, row in enumerate(rows):
                            try:
                                row_text = await row.inner_text()
                                
                                # 검색된 차량번호 패턴을 포함하는 행 찾기 (UI 테스트와 동일)
                                if car_number in row_text or any(char.isdigit() for char in row_text):
                                    
                                    # 행 클릭 시도 (onclick 핸들러가 있는 경우) - UI 테스트와 동일
                                    try:
                                        # 먼저 행 자체에 onclick이 있는지 확인
                                        onclick_attr = await row.get_attribute('onclick')
                                        if onclick_attr:
                                            await row.click()
                                            # 선택 후 대기
                                            await self.page.wait_for_timeout(2000)
                                            return True
                                        else:
                                            # onclick이 없으면 셀 클릭 시도 - UI 테스트와 동일
                                            cells = await row.locator('td').all()
                                            for cell in cells:
                                                if await cell.count() > 0:
                                                    await cell.click()
                                                    await self.page.wait_for_timeout(2000)
                                                    return True
                                                    
                                    except Exception as click_error:
                                        self.logger.log_warning(f"[경고] 행 클릭 중 오류: {str(click_error)}")
                                        continue
                                            
                            except Exception as row_error:
                                self.logger.log_warning(f"[경고] 행 처리 중 오류: {str(row_error)}")
                                continue
                        
                        break
                        
                except Exception:
                    continue
            
            self.logger.log_error(ErrorCode.FAIL_SEARCH, "테이블검색", "검색 결과 테이블을 찾을 수 없음")
            return False
            
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_SEARCH, "차량선택", str(e))
            return False

    async def _debug_page_state(self):
        """디버깅을 위한 페이지 상태 출력"""
        pass


    async def _safe_page_check(self) -> bool:
        """페이지 안전성 검사 (92번 지침 패턴)"""
        try:
            # 1. 페이지 닫힘 상태 확인
            if self.page.is_closed():
                self.logger.log_warning("페이지가 이미 닫혔습니다 - 파싱 불가")
                return False
            
            # 2. URL 접근 가능성 확인
            try:
                current_url = self.page.url
            except Exception as e:
                self.logger.log_warning(f"페이지 상태 확인 실패: {str(e)}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_PARSE, "페이지안전성", f"안전성 검사 실패: {str(e)}")
            return False

    def _empty_coupon_history(self, vehicle_id: str) -> CouponHistory:
        """빈 쿠폰 이력 반환"""
        return CouponHistory(
            store_id=self.store_id,
            vehicle_id=vehicle_id,
            my_history={},
            total_history={},
            available_coupons={}
        )

    async def _parse_coupon_history_c_store(self, total_history: Dict):
        """쿠폰 사용 이력 파싱 - C 매장 전용 (CommonCouponCalculator 사용)"""
        try:
            # 페이지 안전성 검사
            if not await self._safe_page_check():
                return
            
            # C 매장 설정에서 정보 가져오기 (YAML 파일에서 직접 로드)
            from shared.utils.common_coupon_calculator import CommonCouponCalculator
            import yaml
            from pathlib import Path
            
            # C 매장 설정 로드 (YAML 파일에서 직접)
            config_path = Path("infrastructure/config/store_configs/c_store_config.yaml")
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 쿠폰 관련 설정 추출
            coupon_config = config.get('selectors', {}).get('coupons', {})
            coupon_key_mapping = coupon_config.get('coupon_key_mapping', {})
            discount_selectors = coupon_config.get('discount_selectors', [])
            has_my_history = coupon_config.get('table_structure', {}).get('has_my_history', False)
            
            
            # 할인 내역 테이블이 로드될 때까지 대기
            try:
                await self.page.wait_for_selector("tbody[id='discountlist']", timeout=5000)
            except:
                self.logger.log_warning("할인 내역 테이블을 찾을 수 없음")
            
            # 공통 유틸리티로 파싱 (C 매장은 my_history 사용 안함)
            my_history, parsed_total_history = await CommonCouponCalculator.parse_applied_coupons(
                self.page,
                coupon_key_mapping,
                discount_selectors,
                has_my_history=has_my_history
            )
            
            # C 매장 특성: my_history는 항상 빈 딕셔너리, total_history만 사용
            total_history.clear()
            total_history.update(parsed_total_history)
            
            # CommonCouponCalculator가 실패했을 경우 C 매장 전용 로직 시도
            if not total_history:
                try:
                    # 할인내역 테이블에서 직접 파싱
                    for selector in discount_selectors:
                        if await self.page.locator(selector).count() > 0:
                            rows = await self.page.locator(selector).all()
                            
                            for idx, row in enumerate(rows):
                                try:
                                    cells = await row.locator('td').all()
                                    if len(cells) >= 4:
                                        cell_texts = []
                                        for cell in cells:
                                            cell_text = await cell.inner_text()
                                            cell_texts.append(cell_text.strip())
                                        
                                        # C 매장 구조: 삭제 | 날짜 | 할인권명 | 수량
                                        if len(cell_texts) >= 4:
                                            coupon_name = cell_texts[2]  # 할인권명
                                            quantity_text = cell_texts[3]  # 수량
                                            
                                            # 수량 추출
                                            import re
                                            quantity_match = re.search(r'(\d+)', quantity_text)
                                            quantity = int(quantity_match.group(1)) if quantity_match else 1
                                            
                                            # 쿠폰 키 매핑
                                            for mapped_name, coupon_key in coupon_key_mapping.items():
                                                if mapped_name in coupon_name:
                                                    total_history[coupon_key] = total_history.get(coupon_key, 0) + quantity
                                                    break
                                                
                                except Exception as row_e:
                                    continue
                            break
                                    
                except Exception as direct_e:
                    self.logger.log_warning(f"직접 파싱 실패: {str(direct_e)}")
            
                
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_PARSE, "쿠폰이력파싱", str(e))

    async def cleanup(self) -> None:
        """리소스 정리"""
        await super().cleanup()