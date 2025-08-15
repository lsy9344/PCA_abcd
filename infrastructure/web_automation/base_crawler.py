from abc import ABC, abstractmethod
from playwright.async_api import async_playwright, Browser, Page
from typing import Dict, Any, Optional, List
import os
import asyncio
import re
from playwright.async_api import async_playwright

from core.domain.repositories.store_repository import StoreRepository
from core.domain.models.store import StoreConfig
from core.domain.models.vehicle import Vehicle
from core.domain.models.coupon import CouponHistory, CouponApplication
from infrastructure.logging.structured_logger import StructuredLogger

class BaseCrawler(ABC):
    def __init__(self, store_config, playwright_config, structured_logger, notification_service=None):
        self.store_config = store_config
        self.playwright_config = playwright_config
        self.logger = structured_logger
        self.notification_service = notification_service
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.store_id = getattr(store_config, 'store_id', 'UNKNOWN')

    async def _initialize_browser(self) -> None:
        """
        Lambda 환경에 최적화된 브라우저 초기화.
        더 많은 최적화 옵션을 추가하고 타임아웃을 90초로 늘려 콜드 스타트 문제를 해결합니다.
        """
        try:
            # Playwright 인스턴스 시작
            self.playwright = await async_playwright().start()

            # Lambda 환경을 위한 최종 최적화 브라우저 옵션
            browser_args = [
                # --- 핵심 호환성 옵션 ---
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--single-process',
                '--no-zygote',
                
                # --- 리소스 사용량 최소화 옵션 ---
                '--disable-gpu',
                '--disable-software-rasterizer',
                '--disable-extensions',
                '--disable-component-update',
                '--disable-default-apps',
                '--disable-client-side-phishing-detection',
                '--disable-sync',
                '--disable-background-networking',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-breakpad',
                '--disable-hang-monitor',
                '--disable-features=VizDisplayCompositor,TranslateUI',
                '--mute-audio',
                '--hide-scrollbars',
                
                # --- 화면 설정 ---
                '--window-size=1920,1080',
            ]
            
            # playwright_config에서 UI 모드 설정 확인
            headless_mode = self.playwright_config.get('headless', True)
            slow_mo = self.playwright_config.get('slow_mo', 0)
            custom_args = self.playwright_config.get('args', [])
            
            # UI 모드인 경우 일부 Lambda 최적화 옵션 제거
            if not headless_mode:
                browser_args = [arg for arg in browser_args if arg not in [
                    '--single-process', '--no-zygote', '--disable-gpu'
                ]]
                browser_args.extend(custom_args)
            
            # 브라우저 시작 (타임아웃 90초로 대폭 증가)
            self.browser = await self.playwright.chromium.launch(
                headless=headless_mode,
                slow_mo=slow_mo,
                args=browser_args,
                timeout=90000  # 60초 -> 90초로 타임아웃 증가
            )
            
            # 컨텍스트 설정
            viewport = self.playwright_config.get('viewport', {'width': 1920, 'height': 1080})
            user_agent = self.playwright_config.get('user_agent', 
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # 컨텍스트 생성
            self.context = await self.browser.new_context(
                viewport=viewport,
                user_agent=user_agent,
                ignore_https_errors=True,
                java_script_enabled=True
            )
            
            # 페이지 생성
            self.page = await self.context.new_page()
            
            # 페이지 타임아웃 설정
            self.page.set_default_timeout(30000)
            self.page.set_default_navigation_timeout(30000)
            
            print("[성공] Browser initialized successfully using Playwright's default path.")
            
        except Exception as e:
            print(f"[실패] Browser initialization failed: {str(e)}")
            await self.cleanup()
            raise RuntimeError(f"Failed to initialize browser: {str(e)}")

    async def cleanup(self) -> None:
        """리소스 정리"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            print(f"[경고] Cleanup warning: {str(e)}")

    async def __aenter__(self):
        await self._initialize_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()

    async def _safe_click(self, selector: str, timeout: int = 5000) -> bool:
        try:
            await self.page.click(selector, timeout=timeout)
            return True
        except Exception as e:
            self.logger.debug(f"클릭 실패 ({selector}): {str(e)}")
            return False

    async def _safe_fill(self, selector: str, value: str, timeout: int = 5000) -> bool:
        try:
            await self.page.fill(selector, value, timeout=timeout)
            return True
        except Exception as e:
            self.logger.debug(f"입력 실패 ({selector}): {str(e)}")
            return False

    async def _safe_wait_for_selector(self, selector: str, timeout: int = 5000) -> bool:
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception as e:
            self.logger.debug(f"셀렉터 대기 실패 ({selector}): {str(e)}")
            return False

    async def _try_multiple_selectors(self, selectors: list[str], action: str = "click") -> bool:
        for selector in selectors:
            try:
                if action == "click":
                    if await self._safe_click(selector):
                        return True
                elif action == "wait":
                    if await self._safe_wait_for_selector(selector):
                        return True
            except:
                continue
        return False

    async def check_no_vehicle_found(self, page: Page, car_number: str) -> bool:
        """
        공통 차량 검색 실패 감지 로직
        모든 매장에서 '검색된 차량이 없습니다'와 유사한 문구를 감지
        """
        no_result_patterns = [
            'text=검색 결과가 없습니다', 'text="검색 결과가 없습니다"',
            'text=검색된 차량이 없습니다', 'text="검색된 차량이 없습니다"',
            'text=차량을 찾을 수 없습니다', 'text="차량을 찾을 수 없습니다"',
            'text=등록된 차량이 없습니다', 'text="등록된 차량이 없습니다"',
            'text=조회 결과가 없습니다', 'text="조회 결과가 없습니다"',
            'text=해당 차량 정보가 없습니다', 'text="해당 차량 정보가 없습니다"'
        ]
        
        try:
            for pattern in no_result_patterns:
                no_result = page.locator(pattern)
                if await no_result.count() > 0:
                    self.logger.warning(f"[경고] 차량번호 '{car_number}' 검색 결과 없음 팝업 감지")
                    
                    # 팝업 닫기 처리
                    await self._close_no_result_popup(page)
                    
                    # 텔레그램 알림 전송
                    await self._send_no_vehicle_notification(car_number)
                    
                    return True
            
            # 텍스트 내용으로도 확인 (더 유연한 감지)
            page_content = await page.content()
            no_vehicle_keywords = [
                "검색된 차량이 없습니다", "검색 결과가 없습니다", 
                "차량을 찾을 수 없습니다", "등록된 차량이 없습니다",
                "조회 결과가 없습니다", "해당 차량 정보가 없습니다"
            ]
            
            for keyword in no_vehicle_keywords:
                if keyword in page_content:
                    self.logger.warning(f"[경고] 페이지 내용에서 차량 검색 실패 감지: {keyword}")
                    await self._send_no_vehicle_notification(car_number)
                    return True
                    
            return False
            
        except Exception as e:
            self.logger.error(f"[실패] 차량 검색 실패 감지 중 오류: {str(e)}")
            return False

    async def check_no_vehicle_found_by_config(self, page: Page, car_number: str) -> bool:
        """
        설정 기반 차량 검색 실패 감지 로직
        YAML 설정의 search_failure_detection 섹션을 사용하여 감지
        """
        try:
            # 설정에서 search_failure_detection 가져오기
            detection_config = getattr(self.store_config, 'search_failure_detection', None)
            if not detection_config:
                # 설정이 없으면 기존 방식으로 fallback
                return await self.check_no_vehicle_found(page, car_number)
            
            methods = detection_config.get('methods', [])
            # 우선순위에 따라 정렬
            methods = sorted(methods, key=lambda x: x.get('priority', 999))
            
            for method in methods:
                method_type = method.get('type')
                
                if await self._try_detection_method(page, method, car_number):
                    self.logger.warning(f"[경고] 차량번호 '{car_number}' 검색 실패 감지됨 (방법: {method_type})")
                    
                    # 설정 기반 팝업 닫기 처리
                    await self._close_failure_popup_by_config(page, detection_config)
                    
                    # 텔레그램 알림 전송
                    await self._send_no_vehicle_notification(car_number)
                    
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"[실패] 설정 기반 차량 검색 실패 감지 중 오류: {str(e)}")
            # 오류 발생 시 기존 방식으로 fallback
            return await self.check_no_vehicle_found(page, car_number)

    async def _try_detection_method(self, page: Page, method: dict, car_number: str) -> bool:
        """개별 감지 방법 시도"""
        try:
            method_type = method.get('type')
            
            if method_type == 'element_text':
                return await self._detect_by_element_text(page, method)
            elif method_type == 'text_pattern':
                return await self._detect_by_text_pattern(page, method)
            elif method_type == 'popup_detection':
                return await self._detect_by_popup(page, method)
            elif method_type == 'locator_check':
                return await self._detect_by_locator(page, method)
            elif method_type == 'table_check':
                return await self._detect_by_table(page, method)
            else:
                self.logger.warning(f"[경고] 알 수 없는 감지 방법: {method_type}")
                return False
                
        except Exception as e:
            self.logger.debug(f"[디버그] 감지 방법 '{method_type}' 실패: {str(e)}")
            return False

    async def _detect_by_element_text(self, page: Page, method: dict) -> bool:
        """특정 요소의 텍스트로 감지"""
        selector = method.get('selector')
        patterns = method.get('patterns', [])
        
        if not selector or not patterns:
            return False
        
        try:
            element = page.locator(selector)
            if await element.count() > 0:
                element_text = await element.first.inner_text()
                for pattern in patterns:
                    if pattern in element_text:
                        return True
        except Exception:
            pass
        
        return False

    async def _detect_by_text_pattern(self, page: Page, method: dict) -> bool:
        """페이지 전체 텍스트 패턴으로 감지"""
        patterns = method.get('patterns', [])
        
        if not patterns:
            return False
        
        try:
            page_content = await page.content()
            for pattern in patterns:
                if pattern in page_content:
                    return True
        except Exception:
            pass
        
        return False

    async def _detect_by_popup(self, page: Page, method: dict) -> bool:
        """팝업창 구조와 텍스트 조합으로 감지"""
        selectors = method.get('selectors', [])
        text_patterns = method.get('text_patterns', [])
        
        if not selectors:
            return False
        
        try:
            for selector in selectors:
                popup_elements = page.locator(selector)
                if await popup_elements.count() > 0:
                    # 팝업이 존재하면 텍스트 패턴도 확인
                    if not text_patterns:
                        return True  # 텍스트 패턴이 없으면 팝업 존재만으로 판단
                    
                    popup_text = await popup_elements.first.inner_text()
                    for pattern in text_patterns:
                        if pattern in popup_text:
                            return True
        except Exception:
            pass
        
        return False

    async def _detect_by_locator(self, page: Page, method: dict) -> bool:
        """Playwright 로케이터 직접 사용으로 감지"""
        locators = method.get('locators', [])
        
        if not locators:
            return False
        
        try:
            for locator_str in locators:
                element = page.locator(locator_str)
                if await element.count() > 0:
                    return True
        except Exception:
            pass
        
        return False

    async def _detect_by_table(self, page: Page, method: dict) -> bool:
        """테이블 기반 감지 (빈 테이블 또는 특정 메시지)"""
        selector = method.get('selector')
        empty_indicators = method.get('empty_indicators', [])
        
        if not selector:
            return False
        
        try:
            table = page.locator(selector)
            if await table.count() > 0:
                table_text = await table.first.inner_text()
                
                # 빈 테이블 지시자 확인
                for indicator in empty_indicators:
                    if indicator in table_text:
                        return True
                        
                # 테이블이 비어있는지 확인 (행이 매우 적은 경우)
                rows = table.locator('tr')
                row_count = await rows.count()
                if row_count <= 1:  # 헤더만 있거나 아예 없는 경우
                    return True
        except Exception:
            pass
        
        return False

    async def _close_failure_popup_by_config(self, page: Page, detection_config: dict):
        """설정 기반 검색 실패 팝업 닫기"""
        try:
            popup_close_config = detection_config.get('popup_close', {})
            selectors = popup_close_config.get('selectors', [])
            
            if not selectors:
                # 설정이 없으면 기존 방식으로 fallback
                await self._close_no_result_popup(page)
                return
            
            for selector in selectors:
                try:
                    close_button = page.locator(selector)
                    if await close_button.count() > 0:
                        await close_button.first.click()
                        await page.wait_for_timeout(1000)
                        self.logger.info(f"[성공] 검색 실패 팝업 닫기 완료: {selector}")
                        return
                except Exception:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"[경고] 설정 기반 팝업 닫기 실패: {str(e)}")
            # fallback으로 기존 방식 시도
            await self._close_no_result_popup(page)

    async def _close_no_result_popup(self, page: Page):
        """검색 결과 없음 팝업 닫기"""
        try:
            close_buttons = [
                'text=OK', 'text="OK"', 'text=확인', 'text="확인"',
                'text=닫기', 'text="닫기"', 'button:has-text("OK")',
                'button:has-text("확인")', 'button:has-text("닫기")'
            ]
            
            for close_button_selector in close_buttons:
                close_button = page.locator(close_button_selector)
                if await close_button.count() > 0:
                    await close_button.click()
                    await page.wait_for_timeout(1000)
                    self.logger.info("[성공] 검색 결과 없음 팝업 닫기 완료")
                    return
                    
        except Exception as e:
            self.logger.warning(f"[경고] 팝업 닫기 실패: {str(e)}")

    async def _send_no_vehicle_notification(self, car_number: str):
        """차량 검색 결과 없음 텔레그램 알림"""
        try:
            if self.notification_service:
                message = f"차량 검색 실패 알림\n\n매장: {self.store_id}\n차량번호: {car_number}\n상태: 검색된 차량이 없습니다"
                await self.notification_service.send_success_notification(
                    message=message, 
                    store_id=self.store_id
                )
                self.logger.info("[성공] 차량 검색 실패 텔레그램 알림 전송 완료")
            else:
                self.logger.warning("[경고] 텔레그램 알림 서비스가 설정되지 않음")
                
        except Exception as e:
            self.logger.error(f"[실패] 텔레그램 알림 전송 중 오류: {str(e)}")

    # 추상 메서드 정의 - 모든 매장 크롤러에서 구현해야 함
    @abstractmethod
    async def login(self, vehicle: Vehicle = None) -> bool:
        """로그인 수행 - 매장별 구현 필요"""
        pass
    
    @abstractmethod
    async def search_vehicle(self, vehicle: Vehicle) -> bool:
        """차량 검색 - 매장별 구현 필요"""
        pass
    
    @abstractmethod
    async def get_coupon_history(self, vehicle: Vehicle) -> CouponHistory:
        """쿠폰 이력 조회 - 매장별 구현 필요"""
        pass
    
    @abstractmethod
    async def apply_coupons(self, applications: List[CouponApplication]) -> bool:
        """쿠폰 적용 - 매장별 구현 필요"""
        pass
