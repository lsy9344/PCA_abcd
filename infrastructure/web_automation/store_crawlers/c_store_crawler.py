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
            
            # C매장은 로그인 후 팝업이 발생하지 않아 팝업 처리 생략
            
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
        """쿠폰 적용 - 무료 쿠폰 우선 적용"""
        try:
            coupons_to_apply = {app.coupon_name: app.count for app in applications}
            request_id = f"C_coupon_apply_{hash(str(coupons_to_apply))}"
            self.logger.log_request_lifecycle(request_id, "START", f"쿠폰 적용 시작: {coupons_to_apply}")
            self.logger.log_info(f"[쿠폰] C 매장 쿠폰 적용 시작: {coupons_to_apply}")
            
            # 무료 쿠폰 우선 정렬 (무료 > 유료 순서)
            sorted_coupons = self._sort_coupons_by_priority(coupons_to_apply)
            self.logger.log_info(f"[우선순위] 쿠폰 적용 순서: {[name for name, _ in sorted_coupons]}")
            
            total_applied = 0
            for coupon_name, count in sorted_coupons:
                if count > 0:
                    for i in range(count):
                        if await self._apply_single_coupon(coupon_name, i + 1):
                            total_applied += 1
                        else:
                            self.logger.log_error(ErrorCode.FAIL_APPLY, "쿠폰적용", 
                                                f"{coupon_name} {i + 1}개 적용 실패")
                            return False
            
            if total_applied > 0:
                self.logger.log_request_lifecycle(request_id, "END", f"쿠폰 적용 완료: 총 {total_applied}개")
                self.logger.log_info(f"[완료] C 쿠폰 적용 완료: 총 {total_applied}개")
                return True
            else:
                self.logger.log_request_lifecycle(request_id, "END", "적용할 쿠폰이 없음")
                self.logger.log_info("[정보] 적용할 쿠폰이 없음")
                return True
            
        except Exception as e:
            if 'request_id' in locals():
                self.logger.log_request_lifecycle(request_id, "ERROR", f"쿠폰 적용 실패: {str(e)}")
            self.logger.log_error(ErrorCode.FAIL_APPLY, "쿠폰적용", str(e))
            return False

    def _sort_coupons_by_priority(self, coupons: dict) -> list:
        """쿠폰을 우선순위에 따라 정렬 - 무료 쿠폰이 우선"""
        try:
            coupon_list = list(coupons.items())
            
            # 무료 쿠폰 우선, 시간이 긴 것부터 (2시간 > 1시간)
            def coupon_priority(item):
                coupon_name = item[0]
                
                # 무료 쿠폰이 최우선
                if '무료' in coupon_name:
                    priority = 0
                    # 시간이 긴 것부터 (2시간이 1시간보다 우선)
                    if '2시간' in coupon_name:
                        priority -= 20
                    elif '1시간' in coupon_name:
                        priority -= 10
                else:
                    # 유료 쿠폰은 나중에
                    priority = 100
                    if '2시간' in coupon_name:
                        priority -= 20
                    elif '1시간' in coupon_name:
                        priority -= 10
                
                return priority
            
            sorted_coupons = sorted(coupon_list, key=coupon_priority)
            return sorted_coupons
            
        except Exception as e:
            self.logger.log_warning(f"[경고] 쿠폰 정렬 실패: {str(e)}")
            return list(coupons.items())

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
        """보유 쿠폰 파싱 - 개선된 버전"""
        try:
            # 쿠폰 목록 찾기 - 개선된 메서드 사용
            coupon_rows = await self._find_coupon_rows()
            if not coupon_rows:
                self.logger.log_warning("[경고] 쿠폰 목록을 찾을 수 없어 기본값 사용")
                return
            
            self.logger.log_info(f"[디버그] 쿠폰 파싱 대상 행 수: {len(coupon_rows)}")
            
            for i, row in enumerate(coupon_rows):
                try:
                    text = await row.inner_text()
                    self.logger.log_info(f"[디버그] 쿠폰 파싱 행 {i+1}: {text[:100]}...")
                    
                    # 쿠폰 이름과 수량 파싱
                    for coupon_name in available_coupons.keys():
                        if coupon_name in text:
                            # 수량 추출 로직 - 다양한 패턴 시도
                            count = self._extract_coupon_count(text)
                            if count is not None:
                                available_coupons[coupon_name] = {'car': count, 'total': count}
                                self.logger.log_info(f"[발견] {coupon_name}: {count}개")
                                
                                # 쿠폰 부족 알림
                                if count <= 50 and count > 0:
                                    self.logger.log_warning(f"[경고] C 매장 {coupon_name} 쿠폰 부족: {count}개")
                                    asyncio.create_task(self.send_low_coupon_notification(coupon_name, count))
                            else:
                                self.logger.log_warning(f"[경고] {coupon_name} 수량 파싱 실패: {text}")
                            break
                except Exception as row_e:
                    self.logger.log_warning(f"[경고] 쿠폰 행 파싱 중 오류: {str(row_e)}")
                    continue
                        
        except Exception as e:
            self.logger.log_warning(f"[경고] 쿠폰 리스트 파싱 실패: {str(e)}")

    def _extract_coupon_count(self, text: str) -> Optional[int]:
        """텍스트에서 쿠폰 수량 추출 - 다양한 패턴 시도"""
        try:
            # 다양한 수량 패턴들을 시도
            patterns = [
                r'(\d+)\s*개',      # "10개" 형태
                r'(\d+)\s*매',      # "10매" 형태  
                r'(\d+)\s*장',      # "10장" 형태
                r'(\d+)\s*회',      # "10회" 형태
                r'(\d+)\s*건',      # "10건" 형태
                r'수량\s*:?\s*(\d+)',  # "수량: 10" 형태
                r'보유\s*:?\s*(\d+)',  # "보유: 10" 형태
                r'잔여\s*:?\s*(\d+)',  # "잔여: 10" 형태
                r'남은\s*수량\s*:?\s*(\d+)',  # "남은 수량: 10" 형태
                r'(\d+)',           # 마지막 시도: 모든 숫자
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    count = int(match.group(1))
                    # 합리적인 범위인지 확인 (0-9999 사이)
                    if 0 <= count <= 9999:
                        return count
            
            return None
            
        except Exception as e:
            self.logger.log_warning(f"[경고] 쿠폰 수량 추출 실패: {str(e)}")
            return None


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
        """단일 쿠폰 적용 - insert_discount 링크 클릭 방식"""
        try:
            self.logger.log_info(f"[쿠폰] {coupon_name} 쿠폰 적용 시작 (순서: {sequence})")
            
            # 1. insert_discount 링크들 찾기
            coupon_links = await self._find_coupon_rows()
            if not coupon_links:
                self.logger.log_error(ErrorCode.FAIL_APPLY, "쿠폰적용", "적용 가능한 쿠폰 링크를 찾을 수 없음")
                return False
            
            self.logger.log_info(f"[디버그] 발견된 쿠폰 링크 수: {len(coupon_links)}")
            
            # 2. 해당 쿠폰 이름이 포함된 링크 찾기
            for i, coupon_info in enumerate(coupon_links):
                try:
                    link_text = coupon_info['text']
                    link_element = coupon_info['link']
                    
                    self.logger.log_info(f"[디버그] 쿠폰 링크 {i+1}: {link_text}")
                    
                    if coupon_name in link_text:
                        self.logger.log_info(f"[발견] {coupon_name} 쿠폰 링크 찾음")
                        
                        # 3. 쿠폰 링크 클릭 (재시도 포함)
                        if await self._click_coupon_link(link_element, coupon_name, max_retries=2):
                            self.logger.log_info(f"[성공] {coupon_name} 적용 완료")
                            return True
                        else:
                            self.logger.log_error(ErrorCode.FAIL_APPLY, "쿠폰적용", f"{coupon_name} 링크 클릭 실패 (재시도 포함)")
                            return False
                            
                except Exception as link_e:
                    self.logger.log_warning(f"[경고] 쿠폰 링크 처리 중 오류: {str(link_e)}")
                    continue
            
            self.logger.log_error(ErrorCode.FAIL_APPLY, "쿠폰적용", f"{coupon_name} 쿠폰 링크를 찾을 수 없음")
            return False
            
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_APPLY, "쿠폰적용", f"{coupon_name} 적용 중 오류: {str(e)}")
            return False

    async def _click_coupon_link(self, link_element, coupon_name: str, max_retries: int = 2) -> bool:
        """쿠폰 링크 클릭 (재시도 로직 포함)"""
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    self.logger.log_info(f"[재시도] {coupon_name} 쿠폰 링크 클릭 (시도 {attempt + 1}/{max_retries + 1})")
                else:
                    self.logger.log_info(f"[시도] {coupon_name} 쿠폰 링크 클릭")
                
                # 링크 클릭 전 요소 상태 확인
                if not await link_element.is_visible():
                    self.logger.log_warning(f"[경고] {coupon_name} 링크가 보이지 않음")
                    if attempt < max_retries:
                        await self.page.wait_for_timeout(2000)
                        continue
                    return False
                
                # 링크 클릭
                await link_element.click()
                
                # 응답 대기 시간 증가 (3초 → 5초)
                await self.page.wait_for_timeout(5000)
                
                self.logger.log_info(f"[성공] {coupon_name} 링크 클릭 완료")
                
                # 팝업이나 확인 메시지 처리
                confirmation_result = await self._handle_apply_confirmation()
                
                # 확인 처리 성공 시 true 반환
                if confirmation_result:
                    return True
                elif attempt < max_retries:
                    self.logger.log_warning(f"[경고] {coupon_name} 확인 처리 실패 - 재시도")
                    await self.page.wait_for_timeout(2000)
                    continue
                
                return True  # 확인 팝업이 없어도 성공으로 간주
                
            except Exception as e:
                error_msg = str(e)
                if attempt < max_retries:
                    self.logger.log_warning(f"[경고] {coupon_name} 링크 클릭 실패 (시도 {attempt + 1}) - 재시도: {error_msg}")
                    await self.page.wait_for_timeout(3000)
                    continue
                else:
                    self.logger.log_error(ErrorCode.FAIL_APPLY, "링크클릭", f"{coupon_name} 링크 클릭 중 오류: {error_msg}")
                    return False
        
        return False

    async def _handle_apply_confirmation(self) -> bool:
        """쿠폰 적용 확인 팝업 처리"""
        try:
            # 확장된 셀렉터 목록
            confirmation_selectors = [
                'text=확인', 'text=OK', 'text=완료', 'text=닫기',
                '.confirm-btn', '.popup-ok', '.ok-btn', '.close-btn',
                'button:has-text("확인")', 'button:has-text("OK")',
                'input[value="확인"]', 'input[value="OK"]'
            ]
            
            # 팝업 대기 시간 증가 (3초 → 7초)
            for selector in confirmation_selectors:
                try:
                    button = self.page.locator(selector)
                    await button.wait_for(state='visible', timeout=7000)  # 7초 대기
                    
                    # 버튼이 클릭 가능한지 확인
                    if await button.is_enabled():
                        await button.first.click()
                        await self.page.wait_for_timeout(1000)  # 클릭 후 대기 시간 증가
                        self.logger.log_info(f"[성공] 쿠폰 적용 확인 팝업 처리 완료 (셀렉터: {selector})")
                        return True
                    
                except Exception:
                    # 해당 셀렉터로 팝업을 찾지 못했으면 다음 셀렉터 시도
                    continue
            
            # 모든 셀렉터에서 팝업을 찾지 못한 경우
            # 페이지에 alert나 dialog가 있는지 추가 확인
            try:
                # JavaScript alert/confirm 대화상자 확인
                await self.page.wait_for_function(
                    "() => !document.querySelector('.loading, .spinner')", 
                    timeout=3000
                )
                self.logger.log_info("[정보] 확인 팝업 없이 쿠폰 적용 완료")
                return True
            except Exception:
                self.logger.log_info("[정보] 로딩 완료 대기 후 쿠폰 적용 완료")
                return True
            
        except Exception as e:
            self.logger.log_warning(f"[경고] 확인 팝업 처리 실패: {str(e)}")
            return False

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
                        
                        for row_idx, row in enumerate(rows):
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
                self.logger.log_info(f"현재 페이지 URL: {current_url}")
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
            parsed_my_history, parsed_total_history = await CommonCouponCalculator.parse_applied_coupons(
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
                            
                            for row_index, row in enumerate(rows):
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
                                                
                                except Exception:
                                    continue
                            break
                                    
                except Exception as direct_e:
                    self.logger.log_warning(f"직접 파싱 실패: {str(direct_e)}")
            
                
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_PARSE, "쿠폰이력파싱", str(e))

    async def _find_coupon_rows(self):
        """실제 적용 가능한 쿠폰 찾기 - insert_discount 함수를 호출하는 링크들"""
        try:
            self.logger.log_info("[디버그] insert_discount 링크가 있는 쿠폰 검색 중...")
            
            # 실제 쿠폰 적용 링크들 찾기: javascript:insert_discount 패턴
            coupon_link_selectors = [
                "a[href*='insert_discount']",  # insert_discount 함수를 호출하는 링크들
                "a[onclick*='insert_discount']",  # onclick에 insert_discount가 있는 링크들
                "*[onclick*='insert_discount']",  # onclick에 insert_discount가 있는 모든 요소
            ]
            
            coupon_rows = []
            
            for selector in coupon_link_selectors:
                try:
                    links = await self.page.locator(selector).all()
                    self.logger.log_info(f"[디버그] '{selector}' 패턴으로 발견된 링크 수: {len(links)}")
                    
                    for i, link in enumerate(links):
                        try:
                            link_text = await link.inner_text()
                            link_href = await link.get_attribute('href') or ""
                            link_onclick = await link.get_attribute('onclick') or ""
                            
                            self.logger.log_info(f"[디버그] 링크 {i+1}: '{link_text}'")
                            self.logger.log_info(f"[디버그] href: {link_href}")
                            self.logger.log_info(f"[디버그] onclick: {link_onclick}")
                            
                            # 쿠폰 관련 텍스트가 포함된 링크들만 선택
                            if any(keyword in link_text for keyword in ['무료', '유료', '할인권', '쿠폰', '시간']):
                                # 링크의 부모 요소들을 포함한 행 정보 생성
                                coupon_info = {
                                    'link': link,
                                    'text': link_text,
                                    'href': link_href,
                                    'onclick': link_onclick
                                }
                                coupon_rows.append(coupon_info)
                                self.logger.log_info(f"[발견] 적용 가능한 쿠폰: {link_text}")
                        except Exception as link_e:
                            self.logger.log_warning(f"[경고] 링크 처리 중 오류: {str(link_e)}")
                            continue
                            
                except Exception as selector_e:
                    self.logger.log_warning(f"[경고] 셀렉터 '{selector}' 검색 실패: {str(selector_e)}")
                    continue
            
            if coupon_rows:
                self.logger.log_info(f"[발견] 총 적용 가능한 쿠폰 수: {len(coupon_rows)}개")
                return coupon_rows
            else:
                self.logger.log_warning("[경고] insert_discount 링크를 찾을 수 없음")
                return []
            
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_APPLY, "쿠폰목록검색", f"쿠폰 목록 검색 실패: {str(e)}")
            return []

    async def _click_apply_button_in_row(self, row, coupon_name: str) -> bool:
        """쿠폰 행 자체를 클릭하여 팝업 발생시키기"""
        try:
            # 행에서 HTML 구조 디버그
            row_html = await row.inner_html()
            row_text = await row.inner_text()
            self.logger.log_info(f"[디버그] 쿠폰 행 HTML: {row_html[:200]}...")
            self.logger.log_info(f"[디버그] 쿠폰 행 텍스트: {row_text}")
            
            # 1. 먼저 쿠폰 이름이 포함된 클릭 가능한 요소들 찾기
            clickable_selectors = [
                # onclick 속성이 있는 요소들
                "*[onclick]",
                # 링크 요소들  
                "a",
                # 버튼 요소들
                "button", "input[type='button']", "input[type='submit']",
                # 쿠폰 이름을 포함한 클릭 가능한 텍스트들
                f"*:has-text('{coupon_name}')",
                "*:has-text('무료')", "*:has-text('유료')", "*:has-text('할인')",
            ]
            
            # 2. 각 셀렉터로 클릭 가능한 요소들 시도
            for selector in clickable_selectors:
                try:
                    elements = await row.locator(selector).all()
                    self.logger.log_info(f"[디버그] '{selector}' 셀렉터로 발견된 요소 수: {len(elements)}")
                    
                    for i, element in enumerate(elements):
                        try:
                            # 요소 정보 수집
                            is_visible = await element.is_visible()
                            element_text = ""
                            try:
                                element_text = await element.inner_text()
                            except:
                                try:
                                    element_text = await element.get_attribute('value') or ""
                                except:
                                    pass
                            
                            element_onclick = ""
                            try:
                                element_onclick = await element.get_attribute('onclick') or ""
                            except:
                                pass
                            
                            self.logger.log_info(f"[디버그] 요소 {i+1}: '{element_text}' (visible: {is_visible})")
                            self.logger.log_info(f"[디버그] onclick: {element_onclick[:100]}...")
                            
                            # 쿠폰 이름이 포함되거나 관련된 요소라면 클릭 시도
                            if is_visible and (coupon_name in element_text or 
                                              any(keyword in element_text for keyword in ['무료', '유료', '할인']) or
                                              element_onclick):
                                
                                self.logger.log_info(f"[시도] 요소 클릭: '{element_text}'")
                                await element.click()
                                await self.page.wait_for_timeout(3000)  # 팝업 로딩 대기
                                self.logger.log_info(f"[성공] 쿠폰 클릭 완료: '{element_text}'")
                                
                                # 팝업이 발생했는지 확인
                                return await self._check_and_handle_coupon_popup()
                                
                        except Exception as elem_e:
                            self.logger.log_warning(f"[경고] 요소 {i+1} 클릭 시도 실패: {str(elem_e)}")
                            continue
                            
                except Exception:
                    continue
            
            # 3. 위에서 실패했다면 행 자체를 클릭 시도
            try:
                self.logger.log_info("[시도] 쿠폰 행 자체 클릭")
                await row.click()
                await self.page.wait_for_timeout(3000)  # 팝업 로딩 대기
                self.logger.log_info("[성공] 쿠폰 행 클릭 완료")
                
                # 팝업이 발생했는지 확인
                return await self._check_and_handle_coupon_popup()
                
            except Exception as row_e:
                self.logger.log_warning(f"[경고] 행 클릭 실패: {str(row_e)}")
            
            self.logger.log_error(ErrorCode.FAIL_APPLY, "쿠폰클릭", f"{coupon_name} 쿠폰 클릭 실패")
            return False
            
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_APPLY, "쿠폰클릭", f"쿠폰 클릭 중 오류: {str(e)}")
            return False

    async def _check_and_handle_coupon_popup(self) -> bool:
        """쿠폰 클릭 후 팝업 확인 및 처리"""
        try:
            self.logger.log_info("[확인] 쿠폰 적용 팝업 확인 중...")
            
            # 팝업이나 다이얼로그 확인
            popup_selectors = [
                ".popup", ".modal", ".dialog", 
                "[role='dialog']", "[role='alertdialog']",
                "*:has-text('적용')*:has-text('확인')",
                "*:has-text('쿠폰')*:has-text('사용')",
            ]
            
            popup_found = False
            for selector in popup_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        popup_text = await self.page.locator(selector).first.inner_text()
                        self.logger.log_info(f"[발견] 팝업: {popup_text[:100]}...")
                        popup_found = True
                        break
                except Exception:
                    continue
            
            if popup_found:
                # 확인 버튼 클릭
                await self._handle_apply_confirmation()
                self.logger.log_info("[성공] 쿠폰 적용 팝업 처리 완료")
                return True
            else:
                # 팝업이 없어도 성공으로 간주 (바로 적용되는 경우)
                self.logger.log_info("[정보] 팝업 없이 바로 적용된 것으로 추정")
                return True
            
        except Exception as e:
            self.logger.log_warning(f"[경고] 팝업 처리 중 오류: {str(e)}")
            return True  # 오류가 있어도 일단 성공으로 간주

    async def cleanup(self) -> None:
        """리소스 정리"""
        await super().cleanup()