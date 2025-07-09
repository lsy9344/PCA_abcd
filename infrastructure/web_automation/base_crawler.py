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
        """
        Lambda 환경에 최적화된 브라우저 초기화.
        복잡한 경로 탐색 로직을 제거하고 Playwright가 자동으로 브라우저를 찾도록 수정.
        Dockerfile의 ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright 설정을 따릅니다.
        """
        try:
            # Playwright 인스턴스 시작
            self.playwright = await async_playwright().start()

            # Lambda 전용 브라우저 옵션
            browser_args = [
                # 🔥 Lambda 필수 옵션들
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--single-process',
                '--no-zygote',
                '--disable-dev-shm-usage',
                
                # 성능 최적화
                '--disable-gpu',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                
                # 화면 설정
                '--window-size=1920,1080',
            ]
            
            # 브라우저 시작 (executable_path 없이 Playwright가 자동으로 찾도록 함)
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=browser_args,
                timeout=30000  # 30초 타임아웃
            )
            
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
            
            print("✅ Browser initialized successfully using Playwright's default path.")
            
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
