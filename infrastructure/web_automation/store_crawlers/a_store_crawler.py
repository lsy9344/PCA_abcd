"""
A매장 크롤러 구현
"""
import re
import asyncio
from typing import List, Dict, Tuple
from playwright.async_api import TimeoutError

from infrastructure.web_automation.base_crawler import BaseCrawler
from core.domain.models.vehicle import Vehicle
from core.domain.models.coupon import CouponHistory, CouponApplication
from shared.exceptions.automation_exceptions import (
    LoginFailedException, VehicleNotFoundException, CouponHistoryException, CouponApplicationException
)
from infrastructure.config.config_manager import ConfigManager
from infrastructure.logging.structured_logger import StructuredLogger
from utils.optimized_logger import OptimizedLogger, ErrorCode
from utils.optimized_logger import get_optimized_logger


class AStoreCrawler(BaseCrawler):
    """A매장 크롤러"""
    
    def __init__(self, store_config, playwright_config, structured_logger: StructuredLogger, notification_service=None):
        super().__init__(store_config, playwright_config, structured_logger)
        self.logger = OptimizedLogger("a_store_crawler", "A")  # 최적화된 로거 사용
        self.notification_service = notification_service
    
    async def login(self) -> bool:
        """로그인 수행 (팝업 처리 포함)"""
        try:
            await self._initialize_browser()
            
            # 웹사이트 접속
            await self.page.goto(self.store_config.website_url)
            
            # 개발 환경에서만 시작 로그 기록
            self.logger.log_info("[시작] A 매장 자동화 시작")
            
            # 1. 인트로 팝업 닫기 (실패해도 진행)
            try:
                await self.page.click("#skip")
                self.logger.log_info("[팝업처리] 인트로 팝업 닫기 성공")
            except Exception:
                pass  # 팝업 처리 실패는 로그 기록하지 않음

            # 2. 공지 팝업 닫기 (실패해도 진행)
            try:
                await self.page.click("#popupCancel")
                self.logger.log_info("[팝업처리] 공지 팝업 닫기 성공")
            except Exception:
                pass  # 팝업 처리 실패는 로그 기록하지 않음
            
            # 로그인 폼 입력
            await self.page.fill("#id", self.store_config.login_username)
            await self.page.fill("#password", self.store_config.login_password)
            await self.page.click("#login")
            
            # 로그인 성공 확인 (차량번호 입력란이 보이는지)
            await self.page.wait_for_selector("#carNumber", timeout=30000)
            
            # 개발 환경에서만 성공 로그 기록
            self.logger.log_info("[로그인] 로그인 성공")
            
            # 로그인 성공 후 팝업 처리 (실패해도 진행)
            try:
                await self.page.click('#gohome')
                self.logger.log_info("[로그인 후] 첫 번째 팝업 닫기 버튼 클릭 성공")
            except Exception:
                pass
                
            try:
                await self.page.click('#start')
                self.logger.log_info("[로그인 후] 두 번째 팝업 닫기 버튼 클릭 성공")
            except Exception:
                pass
                
            return True
            
        except TimeoutError:
            # 간소화된 에러 로그 + 텔레그램용 상세 정보 반환
            self.logger.log_error(ErrorCode.FAIL_AUTH, "로그인", "차량번호 입력란이 나타나지 않음")
            return False
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_AUTH, "로그인", str(e))
            return False
    
    async def search_vehicle(self, vehicle: Vehicle) -> bool:
        """차량 검색"""
        try:
            # 차량번호 입력
            await self.page.fill("#carNumber", vehicle.number)
            
            # 개발 환경에서만 입력 성공 로그 기록
            self.logger.log_info('[차량검색] 차량 번호 입력 성공')
            
            # 검색 버튼 클릭 (여러 셀렉터 시도)
            try:
                await self.page.click('button[name="search"]')
            except:
                try:
                    await self.page.click('.btn-search')
                except:
                    await self.page.click('button:has-text("검색")')
            
            # 검색 결과 대기
            await self.page.wait_for_timeout(1000)
            
            # [추가] #parkName의 텍스트가 '검색된 차량이 없습니다.'인지 확인
            try:
                park_name_elem = self.page.locator('#parkName')
                if await park_name_elem.count() > 0:
                    park_name_text = await park_name_elem.inner_text()
                    if '검색된 차량이 없습니다.' in park_name_text:
                        self.logger.log_error(ErrorCode.NO_VEHICLE, "차량검색", f"차량번호 {vehicle.number} 검색 결과 없음")
                        return False
            except Exception:
                pass
            
            # 기존: 검색 결과 확인
            no_result = self.page.locator('text="검색된 차량이 없습니다"')
            if await no_result.count() > 0:
                details = self.logger.log_error("A", "차량검색", "NO_VEHICLE", f"차량번호 {vehicle.number} 검색 결과 없음")
                return False
                
            # 차량 선택 버튼 클릭
            try:
                await self.page.click('#next')
                if self.logger.should_log_info():
                    self.logger.log_info('[차량검색] 차량 선택 버튼 클릭 성공')
                await self.page.wait_for_timeout(5000)
            except Exception as e1:
                try:
                    await self.page.click('button:has-text("차량 선택")')
                    if self.logger.should_log_info():
                        self.logger.log_info('[차량검색] button:has-text("차량 선택") 버튼 클릭 성공')
                    await self.page.wait_for_timeout(3000)
                except Exception as e2:
                    details = self.logger.log_error("A", "차량검색", "FAIL_SEARCH", f"차량 선택 버튼 클릭 실패: {str(e1)}, {str(e2)}")
                    return False
            
            # 개발 환경에서만 성공 로그 기록
            if self.logger.should_log_info():
                self.logger.log_info(f"[차량검색] 차량번호 {vehicle.number} 검색 및 선택 후 페이지 로딩 성공")
            return True
            
        except Exception as e:
            details = self.logger.log_error("A", "차량검색", "FAIL_SEARCH", str(e))
            return False
    
    async def get_coupon_history(self) -> Tuple[Dict[str, Dict[str, int]], Dict[str, int], Dict[str, int]]:
        """쿠폰 이력 조회"""
        try:
            discount_types = self.store_config.discount_types
            discount_info = {name: {'car': 0, 'total': 0} for name in discount_types.values()}
            
            # productList 테이블 로드 대기
            await self.page.wait_for_selector('#productList tr', timeout=30000)
            
            # 쿠폰 없음 체크
            empty_message = await self.page.locator('#productList td.empty').count()
            if empty_message > 0:
                # 개발 환경에서만 쿠폰 없음 로그 기록
                if self.logger.should_log_info():
                    self.logger.log_info("[쿠폰상태] 보유한 쿠폰이 없습니다")
                return discount_info, {name: 0 for name in discount_types.values()}, {name: 0 for name in discount_types.values()}
            
            # 쿠폰이 있는 경우 파싱
            rows = await self.page.locator('#productList tr').all()
            for row in rows:
                try:
                    cells = await row.locator('td').all()
                    if len(cells) >= 2:
                        name = (await cells[0].inner_text()).strip()
                        count_text = (await cells[1].inner_text()).strip()
                        
                        for discount_name in discount_types.values():
                            if discount_name in name:
                                car_count, total_count = 0, 0
                                if '/' in count_text:
                                    parts = count_text.split('/')
                                    car_part = parts[0].strip()
                                    total_part = parts[1].strip()
                                    car_match = re.search(r'(\d+)', car_part)
                                    total_match = re.search(r'(\d+)', total_part)
                                    car_count = int(car_match.group(1)) if car_match else 0
                                    total_count = int(total_match.group(1)) if total_match else 0
                                else:
                                    match = re.search(r'(\d+)', count_text)
                                    car_count = int(match.group(1)) if match else 0
                                    total_count = car_count
                                discount_info[discount_name] = {'car': car_count, 'total': total_count}
                                break
                except Exception:
                    continue  # 파싱 오류는 로그 기록하지 않고 계속 진행
            
            # 개발 환경에서만 현재 보유 쿠폰 로깅
            if self.logger.should_log_info():
                self.logger.log_info(">>>>>[현재 적용 가능한 쿠폰]")
                for name, counts in discount_info.items():
                    self.logger.log_info(f"{name}: {counts['car']}개")
            
            # 우리 매장 쿠폰 내역 (#myDcList)
            my_history = {name: 0 for name in discount_types.values()}
            try:
                my_dc_rows = await self.page.locator('#myDcList tr').all()
                for row in my_dc_rows:
                    cells = await row.locator('td').all()
                    if len(cells) >= 2:
                        name = (await cells[0].inner_text()).strip()
                        count_text = (await cells[1].inner_text()).strip()
                        
                        for discount_name in discount_types.values():
                            if discount_name in name:
                                m = re.search(r'(\d+)', count_text)
                                count = int(m.group(1)) if m else 0
                                my_history[discount_name] = count
                                break
            except Exception:
                pass  # myDcList 처리 실패는 로그 기록하지 않음
            
            # 개발 환경에서만 우리 매장 쿠폰 내역 로깅
            if self.logger.should_log_info():
                self.logger.log_info(">>>>>[우리 매장에서 적용한 쿠폰]")
                for name, count in my_history.items():
                    self.logger.log_info(f"{name}: {count}개")
            
            # 전체 쿠폰 이력 (#allDcList)
            total_history = {name: 0 for name in discount_types.values()}
            try:
                total_rows = await self.page.locator('#allDcList tr').all()
                for row in total_rows:
                    cells = await row.locator('td').all()
                    if len(cells) >= 2:
                        name = (await cells[0].inner_text()).strip()
                        count_text = (await cells[1].inner_text()).strip()
                        
                        for discount_name in discount_types.values():
                            if discount_name in name:
                                m = re.search(r'(\d+)', count_text)
                                count = int(m.group(1)) if m else 0
                                total_history[discount_name] = count
                                break
            except Exception:
                pass  # allDcList 처리 실패는 로그 기록하지 않음
            
            # 개발 환경에서만 전체 쿠폰 이력 로깅
            if self.logger.should_log_info():
                self.logger.log_info(">>>>>[전체 적용된 쿠폰] (다른매장+우리매장)")
                for name, count in total_history.items():
                    self.logger.log_info(f"{name}: {count}개")
            
            # 보유 쿠폰량 체크 및 부족 시 텔레그램 알림 (유료 쿠폰만)
            for coupon_name, counts in discount_info.items():
                car_count = counts['car']
                # A 매장 유료 쿠폰만 체크: "1시간할인권(유료)", "1시간주말할인권(유료)"
                if ('1시간할인권(유료)' in coupon_name or '1시간주말할인권(유료)' in coupon_name) and car_count <= 50 and car_count > 0:
                    # WARNING 레벨로 기록 (프로덕션에서도 기록됨)
                    self.logger.log_warning(f"[경고] A 매장 {coupon_name} 쿠폰 부족: {car_count}개")
                    # 비동기로 알림 전송
                    asyncio.create_task(self._send_low_coupon_notification(coupon_name, car_count))
            
            return discount_info, my_history, total_history
            
        except Exception as e:
            details = self.logger.log_error("A", "쿠폰조회", "FAIL_PARSE", str(e))
            return (
                {name: {'car': 0, 'total': 0} for name in discount_types.values()},
                {name: 0 for name in discount_types.values()},
                {name: 0 for name in discount_types.values()}
            )
    
    async def apply_coupons(self, applications: List[CouponApplication]) -> bool:
        """쿠폰 적용"""
        try:
            for application in applications:
                coupon_name = application.coupon_name
                count = application.count
                
                if count > 0:
                    # 해당 쿠폰의 행 찾기
                    rows = await self.page.locator("#productList tr").all()
                    for row in rows:
                        text = await row.inner_text()
                        if coupon_name in text:
                            # 적용 버튼 찾아서 클릭
                            apply_button = row.locator('button:has-text("적용")')
                            if await apply_button.count() > 0:
                                for _ in range(count):
                                    # 1. 쿠폰 적용 버튼 클릭
                                    await apply_button.click()
                                    
                                    # 개발 환경에서만 적용 버튼 클릭 로그 기록
                                    if self.logger.should_log_info():
                                        self.logger.log_info(f"[쿠폰적용] {coupon_name} 적용 버튼 클릭")
                                    
                                    # 2. 첫 번째 확인 팝업 처리
                                    try:
                                        await self.page.wait_for_selector('#popupOk', timeout=30000)
                                        await self.page.click('#popupOk')
                                        if self.logger.should_log_info():
                                            self.logger.log_info("[쿠폰적용] 첫 번째 확인 팝업 처리 성공")
                                        await self.page.wait_for_timeout(500)
                                    except Exception:
                                        pass  # 팝업 처리 실패는 로그 기록하지 않음
                                    
                                    # 3. 두 번째 확인 팝업 처리
                                    try:
                                        await self.page.wait_for_selector('#popupOk', timeout=30000)
                                        await self.page.click('#popupOk')
                                        if self.logger.should_log_info():
                                            self.logger.log_info("[쿠폰적용] 두 번째 확인 팝업 처리 성공")
                                        await self.page.wait_for_timeout(500)
                                    except Exception:
                                        pass  # 팝업 처리 실패는 로그 기록하지 않음
                                
                                # 개발 환경에서만 적용 성공 로그 기록
                                if self.logger.should_log_info():
                                    self.logger.log_info(f"[쿠폰적용] {coupon_name} {count}개 적용 성공")
                            else:
                                details = self.logger.log_error("A", "쿠폰적용", "FAIL_APPLY", f"{coupon_name} 적용 버튼을 찾을 수 없음")
                                return False
                            break
            
            # 개발 환경에서만 완료 로그 기록
            if self.logger.should_log_info():
                self.logger.log_info(f"[{self.store_config.store_id}][쿠폰적용] 모든 쿠폰 적용 완료")
            return True
            
        except Exception as e:
            details = self.logger.log_error("A", "쿠폰적용", "FAIL_APPLY", str(e))
            return False

    async def _send_low_coupon_notification(self, coupon_name: str, coupon_count: int):
        """쿠폰 부족 텔레그램 알림 (CloudWatch Logs 비용 최적화 적용)"""
        try:
            if self.notification_service:
                message = f"A 매장 보유 쿠폰 충전 필요 알림\n\n"
                message += f"쿠폰 종류: {coupon_name}\n"
                message += f"현재 쿠폰: {coupon_count}개\n"
                message += f"권장 최소량: 50개\n"
                
                await self.notification_service.send_success_notification(
                    message=message,
                    store_id="A"
                )
                # 개발환경에서만 성공 로그 기록
                self.logger.log_info(f"[성공] {coupon_name} 쿠폰 부족 텔레그램 알림 전송 완료")
            else:
                # WARNING 레벨로 기록 (프로덕션에서도 기록됨)
                self.logger.log_warning("[경고] 텔레그램 알림 서비스가 설정되지 않음")
                
        except Exception as e:
            # CloudWatch 비용 절감을 위한 간소화된 에러 로그
            self.logger.log_error(ErrorCode.FAIL_APPLY, "텔레그램알림", str(e))