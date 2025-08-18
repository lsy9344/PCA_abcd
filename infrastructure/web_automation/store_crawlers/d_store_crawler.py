"""
D 매장 크롤러 구현
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


class DStoreCrawler(BaseCrawler, StoreRepository):
    """D 매장 전용 크롤러"""
    
    def __init__(self, store_config: Any, playwright_config: Dict[str, Any], structured_logger: Any, notification_service: Optional[Any] = None):
        super().__init__(store_config, playwright_config, structured_logger, notification_service)
        self.store_id = "D"
        self.user_id = store_config.login_username
        self.logger = OptimizedLogger("d_store_crawler", "D")
    
    async def login(self, vehicle: Optional[Vehicle] = None) -> bool:
        """D 매장 로그인"""
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
            
            # 로그인 후 상태 확인
            await self.page.wait_for_timeout(2000)  # 응답 대기
            
            # 비밀번호 만료 확인
            password_expired = self.page.locator(self.store_config.selectors['popups']['password_expired_popup'])
            if await password_expired.count() > 0:
                self.logger.log_error(ErrorCode.FAIL_AUTH, "로그인", "비밀번호가 만료되었습니다. 비밀번호 재설정이 필요합니다.")
                await self._handle_password_expired_popup()
                return False
            
            # 로그인 성공 확인 - '차량번호 뒤 4자리' 텍스트 확인
            success_indicator = self.store_config.selectors['popups'].get('login_success_indicator', 'text=차량번호 뒤 4자리')
            await self.page.wait_for_selector(success_indicator, timeout=15000)
            self.logger.log_info("[성공] D 매장 로그인 완료 ('차량번호 뒤 4자리' 텍스트 확인) - 팝업 처리 생략하고 차량번호 입력으로 진행")
            
            return True
            
        except TimeoutError:
            self.logger.log_error(ErrorCode.FAIL_AUTH, "로그인", "로그인 후 메인 페이지가 나타나지 않음")
            return False
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_AUTH, "로그인", str(e))
            return False

    async def search_vehicle(self, vehicle: Vehicle) -> bool:
        """차량 검색 및 차량번호 뒤 4자리 크롤링"""
        try:
            car_number = vehicle.number
            
            # 차량번호 직접 입력 (입력필드 찾지 않고 바로 타이핑)
            await self.page.keyboard.type(car_number)
            await self.page.wait_for_timeout(1000)
            
            # 엔터 키로 검색 실행
            await self.page.keyboard.press('Enter')
            await self.page.wait_for_timeout(3000)  # 검색 결과 로딩 대기 시간 증가
            
            # 공통 차량 검색 실패 감지 로직 사용 (설정 기반)
            if await self.check_no_vehicle_found_by_config(self.page, car_number):
                self.logger.log_error(ErrorCode.NO_VEHICLE, "차량검색", f"차량번호 {car_number} 검색 결과 없음")
                return False
            
            # 차량번호 뒤 4자리 크롤링 및 검증
            crawled_last_four = await self._crawl_vehicle_last_four_digits()
            if crawled_last_four:
                expected_last_four = car_number[-4:] if len(car_number) >= 4 else car_number
                if crawled_last_four == expected_last_four:
                    self.logger.log_info(f"[성공] 차량번호 '{car_number}' 검색 및 검증 완료 (뒤 4자리: {crawled_last_four})")
                    return True
                else:
                    self.logger.log_error(ErrorCode.FAIL_SEARCH, "차량검색", 
                                        f"차량번호 불일치 - 입력: {expected_last_four}, 크롤링: {crawled_last_four}")
                    return False
            else:
                self.logger.log_info(f"[성공] 차량번호 '{car_number}' 검색 성공 (차량번호 크롤링 실패했지만 검색은 성공)")
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
            self.logger.log_info(f"[쿠폰] D 매장 쿠폰 적용 시작: {coupons_to_apply}")
            
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
                self.logger.log_info(f"[완료] D 쿠폰 적용 완료: 총 {total_applied}개")
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
                self.store_config.selectors['popups']['alert_ok'],
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

    async def _handle_password_expired_popup(self):
        """비밀번호 만료 팝업 처리"""
        try:
            # 비밀번호 만료 팝업의 확인 버튼 클릭
            popup_selectors = [
                self.store_config.selectors['popups']['ok_button'],
                self.store_config.selectors['popups']['alert_ok'],
                'button:has-text("확인")',
                'button:has-text("OK")'
            ]
            
            for selector in popup_selectors:
                try:
                    button = self.page.locator(selector)
                    if await button.count() > 0:
                        await button.first.click()
                        await self.page.wait_for_timeout(1000)
                        self.logger.log_info(f"[성공] 비밀번호 만료 팝업 처리 완료: {selector}")
                        break
                except Exception:
                    continue
                    
            # 텔레그램 알림 발송
            if self.notification_service:
                message = f"D 매장 계정 비밀번호 만료 알림\n\n계정: {self.user_id}\n상태: 비밀번호 만료\n조치 필요: 시스템 관리자에게 비밀번호 재설정 요청"
                await self.notification_service.send_error_notification(message=message, store_id=self.store_id)
                        
        except Exception as e:
            self.logger.log_warning(f"[경고] 비밀번호 만료 팝업 처리 실패: {str(e)}")

    async def _check_no_vehicle_popup(self):
        """차량 검색 실패 팝업 감지 (구조적 요소 기반)"""
        try:
            # 스크린샷에서 확인된 팝업창 구조적 특징들로 감지
            popup_patterns = [
                # w2window 클래스를 가진 팝업창
                '.w2window.w2window_restored.w2popup_window',
                # alert로 시작하는 ID를 가진 div
                'div[id*="alert"]',
                # 팝업의 특정 구조 (mf_wfm_body_alert로 시작하는 ID)
                'div[id*="mf_wfm_body_alert"]',
                # textarea가 있는 팝업창 (메시지 영역)
                '.w2popup_window textarea',
                # 일반적인 알림 팝업 패턴
                '.w2window .w2window_content'
            ]
            
            for pattern in popup_patterns:
                popup_element = self.page.locator(pattern)
                if await popup_element.count() > 0:
                    self.logger.log_info(f"[감지] 차량검색 실패 팝업 감지됨: {pattern}")
                    return True
            
            return False
        except Exception as e:
            self.logger.log_warning(f"[경고] 팝업 감지 중 오류: {str(e)}")
            return False

    async def _handle_no_result_popup(self):
        """검색 결과 없음 팝업 처리"""
        try:
            # 팝업 닫기 버튼들 시도
            close_buttons = [
                'text=OK', 'text=확인', '.btn-confirm', '.btn-close',
                # w2window 팝업의 일반적인 닫기 버튼들
                '.w2popup_window button',
                '.w2window button[title="닫기"]',
                '.w2window .w2window_close'
            ]
            
            for selector in close_buttons:
                close_button = self.page.locator(selector)
                if await close_button.count() > 0:
                    await close_button.first.click()
                    await self.page.wait_for_timeout(1000)
                    self.logger.log_info("[성공] 검색 결과 없음 팝업 닫기 완료")
                    break
        except Exception as e:
            self.logger.log_warning(f"[경고] 팝업 닫기 실패: {str(e)}")

        else:
            self.logger.log_warning("[경고] 텔레그램 알림 서비스가 설정되지 않음")

    async def send_low_coupon_notification(self, coupon_name: str, coupon_count: int) -> None:
        """쿠폰 부족 텔레그램 알림 (A 매장과 동일한 견고한 에러 처리 적용)"""
        try:
            if self.notification_service:
                message = f"D 매장 보유 쿠폰 충전 필요 알림\n\n"
                message += f"쿠폰 종류: {coupon_name}\n"
                message += f"현재 쿠폰: {coupon_count}개\n"
                message += f"권장 최소량: 50개\n"
                
                await self.notification_service.send_success_notification(
                    message=message,
                    store_id=self.store_id
                )
                # 개발환경에서만 성공 로그 기록
                self.logger.log_info(f"[성공] {coupon_name} 쿠폰 부족 텔레그램 알림 전송 완료")
            else:
                # WARNING 레벨로 기록 (프로덕션에서도 기록됨)
                self.logger.log_warning("[경고] 텔레그램 알림 서비스가 설정되지 않음")
                
        except Exception as e:
            # CloudWatch 비용 절감을 위한 간소화된 에러 로그
            self.logger.log_error(ErrorCode.FAIL_APPLY, "텔레그램알림", str(e))

    async def _parse_available_coupons(self, available_coupons: Dict):
        """보유 쿠폰 파싱 - 실제 D매장 구조에 맞게 수정"""
        try:
            self.logger.log_info("========== _parse_available_coupons 메소드 시작 ==========")
            parsed_coupons = []
            
            # 1단계: 스크린샷에서 확인된 정확한 셀렉터로 시도
            self.logger.log_info("[디버그] 1단계: 정확한 셀렉터로 파싱 시도")
            
            # 1시간 무료 쿠폰 수량 파싱 (정확한 셀렉터)
            hour_coupon_element = self.page.locator('#mf_wfm_body_gen_dcTkList_0_discountTkRemainCnt.w2textbox')
            hour_element_count = await hour_coupon_element.count()
            self.logger.log_info(f"[디버그] 1시간 쿠폰 셀렉터 매칭 개수: {hour_element_count}")
            
            if hour_element_count > 0:
                hour_text = await hour_coupon_element.inner_text()
                self.logger.log_info(f"[디버그] 1시간 쿠폰 텍스트: '{hour_text}'")
                if hour_text and hour_text.strip().replace(',', '').isdigit():
                    hour_count = int(hour_text.strip().replace(',', ''))
                    parsed_coupons.append(hour_count)
                    self.logger.log_info(f"[1단계] 1시간 쿠폰 수량 발견: {hour_count:,}개")
            
            # 30분 유료 쿠폰 수량 파싱 (정확한 셀렉터)
            min_coupon_element = self.page.locator('#mf_wfm_body_gen_dcTkList_1_discountTkRemainCnt.w2textbox')
            min_element_count = await min_coupon_element.count()
            self.logger.log_info(f"[디버그] 30분 쿠폰 셀렉터 매칭 개수: {min_element_count}")
            
            if min_element_count > 0:
                min_text = await min_coupon_element.inner_text()
                self.logger.log_info(f"[디버그] 30분 쿠폰 텍스트: '{min_text}'")
                if min_text and min_text.strip().replace(',', '').isdigit():
                    min_count = int(min_text.strip().replace(',', ''))
                    parsed_coupons.append(min_count)
                    self.logger.log_info(f"[1단계] 30분 쿠폰 수량 발견: {min_count:,}개")
            
            self.logger.log_info(f"[디버그] 1단계 완료, 파싱된 쿠폰 개수: {len(parsed_coupons)}")
            
            # 2단계: fallback으로 모든 가능한 셀렉터 시도
            if not parsed_coupons:
                self.logger.log_info("[디버그] 2단계: fallback으로 파싱 시도")
                
                # 더 광범위한 셀렉터로 모든 w2textbox 검사
                all_textboxes = await self.page.locator('.w2textbox').all()
                self.logger.log_info(f"[디버그] 전체 w2textbox 요소 개수: {len(all_textboxes)}")
                
                found_numbers = []
                for i, textbox in enumerate(all_textboxes[:20]):  # 처음 20개만 검사
                    try:
                        text_content = await textbox.inner_text()
                        if text_content and text_content.strip().replace(',', '').isdigit():
                            number = int(text_content.strip().replace(',', ''))
                            found_numbers.append(number)
                            element_id = await textbox.get_attribute('id') or 'no-id'
                            self.logger.log_info(f"[디버그] w2textbox #{i} (id: {element_id}): {number:,}")
                    except Exception:
                        continue
                
                # 쿠폰 수량으로 보이는 값들 선택
                for number in found_numbers:
                    if number >= 0:
                        parsed_coupons.append(number)
                        self.logger.log_info(f"[2단계] 쿠폰 수량 발견: {number:,}개")
                
                self.logger.log_info(f"[디버그] 2단계 완료, 파싱된 쿠폰 개수: {len(parsed_coupons)}")
                
            # 여기서 else 제거 - 잘못된 조건문에 걸려있었음
            
            # 파싱된 쿠폰을 순서대로 배정 (첫 번째가 1시간, 두 번째가 30분으로 추정)
            if len(parsed_coupons) >= 1:
                # 첫 번째 수량을 1시간 쿠폰으로 할당
                hour_count = parsed_coupons[0]
                available_coupons["1시간 무료"] = {'car': hour_count, 'total': hour_count}
                self.logger.log_info(f"[파싱] 1시간 쿠폰 보유 수량: {hour_count:,}개")
            
            if len(parsed_coupons) >= 2:
                # 두 번째 수량을 30분 쿠폰으로 할당
                min_count = parsed_coupons[1]
                available_coupons["30분 유료"] = {'car': min_count, 'total': min_count}
                self.logger.log_info(f"[파싱] 30분 쿠폰 보유 수량: {min_count:,}개")
            
            # 3단계: 기존 고정 ID 방식으로 최종 fallback
            if not parsed_coupons:
                self.logger.log_info("[디버그] 3단계: 고정 ID 방식으로 fallback 시도")
                
                # 1시간 쿠폰 수량 파싱 (고정 ID)
                hour_coupon_quantity = self.page.locator('#mf_wfm_body_wq_uuid_599 .w2textbox')
                hour_fallback_count = await hour_coupon_quantity.count()
                self.logger.log_info(f"[디버그] 고정 ID 1시간 쿠폰 셀렉터 매칭: {hour_fallback_count}")
                
                if hour_fallback_count > 0:
                    hour_count_text = await hour_coupon_quantity.first.inner_text()
                    self.logger.log_info(f"[디버그] 고정 ID 1시간 쿠폰 텍스트: '{hour_count_text}'")
                    hour_count_match = re.search(r'(\d+)', hour_count_text.replace(',', ''))
                    if hour_count_match:
                        hour_count = int(hour_count_match.group(1))
                        available_coupons["1시간 무료"] = {'car': hour_count, 'total': hour_count}
                        self.logger.log_info(f"[3단계] 1시간 쿠폰 보유 수량 (고정ID): {hour_count:,}개")
                
                # 30분 쿠폰 수량 파싱 (고정 ID)
                min_coupon_quantity = self.page.locator('#mf_wfm_body_wq_uuid_605 .w2textbox')
                min_fallback_count = await min_coupon_quantity.count()
                self.logger.log_info(f"[디버그] 고정 ID 30분 쿠폰 셀렉터 매칭: {min_fallback_count}")
                
                if min_fallback_count > 0:
                    min_count_text = await min_coupon_quantity.first.inner_text()
                    self.logger.log_info(f"[디버그] 고정 ID 30분 쿠폰 텍스트: '{min_count_text}'")
                    min_count_match = re.search(r'(\d+)', min_count_text.replace(',', ''))
                    if min_count_match:
                        min_count = int(min_count_match.group(1))
                        available_coupons["30분 유료"] = {'car': min_count, 'total': min_count}
                        self.logger.log_info(f"[3단계] 30분 쿠폰 보유 수량 (고정ID): {min_count:,}개")
                
                self.logger.log_info("[디버그] 3단계 완료 - 고정 ID 방식 파싱 종료")
                return  # 고정 ID 방식 사용 시 여기서 종료
            
            # 보유 쿠폰량 체크 및 부족 시 텔레그램 알림 (A 매장과 동일한 로직)
            for coupon_name, counts in available_coupons.items():
                if counts.get('total', 0) <= 50 and counts.get('total', 0) > 0:
                    self.logger.log_warning(f"[경고] D 매장 {coupon_name} 쿠폰 부족: {counts['total']}개")
                    asyncio.create_task(self.send_low_coupon_notification(coupon_name, counts['total']))
                        
        except Exception as e:
            self.logger.log_warning(f"[경고] 쿠폰 리스트 파싱 실패: {str(e)}")

    async def _parse_coupon_history(self, my_history: Dict, total_history: Dict):
        """쿠폰 사용 이력 파싱 - 실제 D매장 구조에 맞게 수정"""
        try:
            # 30분 유료 쿠폰 그룹 파싱
            paid_coupon_group = self.page.locator('#mf_wfm_body_gen_usedDcTkGrpList_0_discountTkGrp')
            if await paid_coupon_group.count() > 0:
                # 30분 유료 쿠폰 카운트 추출
                paid_count_element = paid_coupon_group.locator('span')
                if await paid_count_element.count() > 0:
                    paid_count_text = await paid_count_element.first.inner_text()
                    # "(2)" 형태에서 숫자 추출
                    paid_count_match = re.search(r'\((\d+)\)', paid_count_text)
                    if paid_count_match:
                        paid_count = int(paid_count_match.group(1))
                        total_history["30분 유료"] = paid_count
                        my_history["30분 유료"] = paid_count  # D매장은 현재 사용자 기준으로 표시
                        self.logger.log_info(f"[파싱] 30분 유료 쿠폰 이력: {paid_count}개")
            
            # 1시간 무료 쿠폰 그룹 파싱
            free_coupon_group = self.page.locator('#mf_wfm_body_gen_usedDcTkGrpList_1_discountTkGrp')
            if await free_coupon_group.count() > 0:
                # 1시간 무료 쿠폰 카운트 추출
                free_count_element = free_coupon_group.locator('span')
                if await free_count_element.count() > 0:
                    free_count_text = await free_count_element.first.inner_text()
                    # "(1)" 형태에서 숫자 추출
                    free_count_match = re.search(r'\((\d+)\)', free_count_text)
                    if free_count_match:
                        free_count = int(free_count_match.group(1))
                        total_history["1시간 무료"] = free_count
                        my_history["1시간 무료"] = free_count  # D매장은 현재 사용자 기준으로 표시
                        self.logger.log_info(f"[파싱] 1시간 무료 쿠폰 이력: {free_count}개")
            
            # 추가적으로 일반적인 패턴도 시도 (fallback)
            coupon_groups = await self.page.locator('div[id*="usedDcTkGrpList"]').all()
            for group in coupon_groups:
                try:
                    group_text = await group.inner_text()
                    if "30분" in group_text:
                        count_match = re.search(r'\((\d+)\)', group_text)
                        if count_match and "30분 유료" not in total_history:
                            count = int(count_match.group(1))
                            total_history["30분 유료"] = count
                            my_history["30분 유료"] = count
                    elif "1시간" in group_text:
                        count_match = re.search(r'\((\d+)\)', group_text)
                        if count_match and "1시간 무료" not in total_history:
                            count = int(count_match.group(1))
                            total_history["1시간 무료"] = count
                            my_history["1시간 무료"] = count
                except Exception:
                    continue
                        
        except Exception as e:
            self.logger.log_warning(f"[경고] 쿠폰 이력 파싱 실패: {str(e)}")

    def _map_coupon_type(self, coupon_text: str) -> Optional[str]:
        """쿠폰 텍스트를 표준 타입으로 매핑 (실제 D매장 쿠폰명 기준)"""
        if "1시간 무료" in coupon_text or ("1시간" in coupon_text and "무료" in coupon_text):
            return "FREE_COUPON"
        elif "30분 유료" in coupon_text or ("30분" in coupon_text and "유료" in coupon_text):
            return "PAID_COUPON"
        return None

    def _match_coupon_name(self, coupon_name: str, text: str) -> bool:
        """쿠폰명 매칭 헬퍼 (실제 D매장 쿠폰명 기준)"""
        text_lower = text.lower()
        if coupon_name == "1시간 무료":
            return "1시간" in text and "무료" in text
        elif coupon_name == "30분 유료":
            return "30분" in text and "유료" in text
        return False

    async def _apply_single_coupon(self, coupon_name: str, sequence: int) -> bool:
        """단일 쿠폰 적용 - 실제 D매장 구조에 맞게 수정"""
        try:
            self.logger.log_info(f"[쿠폰] {coupon_name} 쿠폰 적용 시작 (순서: {sequence})")
            
            # 쿠폰명에 따른 적용 버튼 셀렉터 결정
            if "1시간" in coupon_name:
                # 1시간 쿠폰 적용 버튼
                apply_button = self.page.locator('#mf_wfm_body_gen_dcTkList_0_discountTkGrp[role="button"]')
            elif "30분" in coupon_name:
                # 30분 쿠폰 적용 버튼
                apply_button = self.page.locator('#mf_wfm_body_gen_dcTkList_1_discountTkGrp[role="button"]')
            else:
                self.logger.log_error(ErrorCode.FAIL_APPLY, "쿠폰적용", f"알 수 없는 쿠폰명: {coupon_name}")
                return False
            
            # 적용 버튼 클릭
            if await apply_button.count() > 0:
                await apply_button.first.click()
                await self.page.wait_for_timeout(1000)
                
                # 확인 팝업은 나타나지 않으므로 팝업 처리 제거
                self.logger.log_info(f"[성공] {coupon_name} 적용 완료 (확인 팝업 없음)")
                return True
            else:
                self.logger.log_error(ErrorCode.FAIL_APPLY, "쿠폰적용", f"{coupon_name} 적용 버튼을 찾을 수 없음")
                return False
            
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_APPLY, "쿠폰적용", f"{coupon_name} 적용 중 오류: {str(e)}")
            return False

    async def _handle_apply_confirmation(self):
        """쿠폰 적용 확인 팝업 처리"""
        try:
            confirmation_selectors = ['text=확인', 'text=OK', '.btn-confirm', '.btn-close']
            for selector in confirmation_selectors:
                button = self.page.locator(selector)
                if await button.count() > 0:
                    await button.first.click()
                    await self.page.wait_for_timeout(500)
                    self.logger.log_info("[성공] 쿠폰 적용 확인 팝업 처리 완료")
                    break
        except Exception as e:
            self.logger.log_warning(f"[경고] 확인 팝업 처리 실패: {str(e)}")

    async def _crawl_vehicle_last_four_digits(self) -> Optional[str]:
        """차량번호 뒤 4자리 크롤링"""
        try:
            await self.page.wait_for_timeout(2000)  # 페이지 로딩 대기
            
            # 우선순위 1: id="mf_wfm_body_carNoText" 요소에서 찾기
            car_number_element = self.page.locator('#mf_wfm_body_carNoText')
            if await car_number_element.count() > 0:
                car_number_text = await car_number_element.first.inner_text()
                if car_number_text and len(car_number_text) >= 4:
                    last_four = car_number_text[-4:]
                    self.logger.log_info(f"[성공] 차량번호 뒤 4자리 크롤링 완료 (id 방식): {last_four}")
                    return last_four
            
            # 우선순위 2: data-title="차량번호" 속성을 가진 요소에서 찾기
            car_number_by_title = self.page.locator('[data-title="차량번호"]')
            if await car_number_by_title.count() > 0:
                # data-title 요소 내부의 텍스트 또는 자식 요소에서 차량번호 찾기
                elements = await car_number_by_title.all()
                for element in elements:
                    try:
                        # 자식 요소가 있는지 확인
                        child_elements = await element.locator('*').all()
                        if child_elements:
                            for child in child_elements:
                                child_text = await child.inner_text()
                                if child_text and self._is_valid_car_number(child_text):
                                    last_four = child_text[-4:]
                                    self.logger.log_info(f"[성공] 차량번호 뒤 4자리 크롤링 완료 (data-title 자식 요소): {last_four}")
                                    return last_four
                        
                        # 직접 텍스트 확인
                        element_text = await element.inner_text()
                        if element_text and self._is_valid_car_number(element_text):
                            last_four = element_text[-4:]
                            self.logger.log_info(f"[성공] 차량번호 뒤 4자리 크롤링 완료 (data-title 직접): {last_four}")
                            return last_four
                            
                    except Exception:
                        continue
            
            # 우선순위 3: 일반적인 차량번호 패턴 검색 (테이블 내에서)
            table_cells = self.page.locator('td, div')
            if await table_cells.count() > 0:
                cells = await table_cells.all()
                for cell in cells[:50]:  # 성능을 위해 처음 50개만 검사
                    try:
                        cell_text = await cell.inner_text()
                        if cell_text and self._is_valid_car_number(cell_text.strip()):
                            last_four = cell_text.strip()[-4:]
                            self.logger.log_info(f"[성공] 차량번호 뒤 4자리 크롤링 완료 (패턴 검색): {last_four}")
                            return last_four
                    except Exception:
                        continue
            
            self.logger.log_warning("[경고] 차량번호 뒤 4자리 크롤링 실패 - 요소를 찾을 수 없음")
            return None
            
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_PARSE, "차량번호크롤링", f"차량번호 뒤 4자리 크롤링 중 오류: {str(e)}")
            return None

    def _is_valid_car_number(self, text: str) -> bool:
        """차량번호 유효성 검사"""
        if not text or len(text) < 4:
            return False
        
        # 한국 차량번호 패턴 확인 (숫자 + 한글 + 숫자 조합)
        import re
        # 예: "12가1234", "123나4567", "33너7367" 등
        car_pattern = r'^\d{2,3}[가-힣]\d{4}$'
        return bool(re.match(car_pattern, text.strip()))

    async def cleanup(self) -> None:
        """리소스 정리"""
        await super().cleanup()