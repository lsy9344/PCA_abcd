from abc import ABC
from playwright.async_api import async_playwright, Browser, Page
from typing import Dict, Any, Optional
import os
import asyncio
from playwright.async_api import async_playwright

from core.domain.repositories.store_repository import StoreRepository
from core.domain.models.store import StoreConfig
from infrastructure.logging.structured_logger import StructuredLogger

class BaseCrawler:
    def __init__(self, store_config, playwright_config, structured_logger):
        self.store_config = store_config
        self.playwright_config = playwright_config
        self.logger = structured_logger
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def _initialize_browser(self) -> None:
        """Lambda 환경에 최적화된 브라우저 초기화"""
        try:
            # Playwright 인스턴스 시작
            self.playwright = await async_playwright().start()
            
            # 🚨 Lambda 전용 Chromium 경로 설정
            # Playwright가 설치한 Chromium 사용 (glibc 호환 보장)
            browser_path = None
            
            # Lambda 환경에서 Playwright Chromium 경로들
            possible_paths = [
                # Playwright 기본 설치 경로 (Lambda 환경)
                "/var/lang/lib/python3.9/site-packages/playwright/driver/package/.local-browsers/chromium-*/chrome-linux/chrome",
                "/opt/python/lib/python3.9/site-packages/playwright/driver/package/.local-browsers/chromium-*/chrome-linux/chrome",
                # 홈 디렉토리 (로컬 개발용)
                os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux/chrome")
            ]
            
            # 경로 찾기 (glob 패턴 처리)
            import glob
            for pattern in possible_paths:
                matches = glob.glob(pattern)
                if matches:
                    browser_path = matches[0]
                    break
            
            # Lambda 전용 브라우저 옵션
            browser_args = [
                # 🔥 Lambda 필수 옵션들
                '--no-sandbox',                    # Lambda 보안 정책상 필수
                '--disable-setuid-sandbox',        # 추가 보안 옵션
                '--single-process',                # 메모리 최적화
                '--no-zygote',                     # 프로세스 최적화
                '--disable-dev-shm-usage',         # 공유 메모리 문제 방지
                
                # 성능 최적화
                '--disable-gpu',                   # GPU 비활성화
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-features=TranslateUI',
                '--disable-ipc-flooding-protection',
                
                # 메모리 최적화
                '--memory-pressure-off',
                '--max_old_space_size=4096',
                '--disable-background-networking',
                
                # 화면 설정
                '--window-size=1920,1080',
                '--virtual-time-budget=10000'
            ]
            
            # 브라우저 시작 옵션
            launch_options = {
                'headless': True,
                'args': browser_args,
                'timeout': 30000,  # 30초 타임아웃
            }
            
            # 경로가 발견되면 명시적으로 설정
            if browser_path and os.path.exists(browser_path):
                launch_options['executable_path'] = browser_path
                print(f"✅ Using Chromium at: {browser_path}")
            else:
                print("⚠️ Using default Chromium path")
            
            # 브라우저 시작
            self.browser = await self.playwright.chromium.launch(**launch_options)
            
            # 컨텍스트 생성 (Lambda 최적화)
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                ignore_https_errors=True,
                java_script_enabled=True,
                timeout=30000
            )
            
            # 페이지 생성
            self.page = await self.context.new_page()
            
            # 페이지 타임아웃 설정
            self.page.set_default_timeout(30000)
            self.page.set_default_navigation_timeout(30000)
            
            print("✅ Browser initialized successfully")
            
        except Exception as e:
            print(f"❌ Browser initialization failed: {str(e)}")
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
            print(f"⚠️ Cleanup warning: {str(e)}")

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
