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
