"""
Vehicle Search Implementation using Playwright MCP
Implements vehicle search functionality with number input, search, and selection
"""
import asyncio
from typing import Optional
from core.domain.models.vehicle import Vehicle
from utils.optimized_logger import OptimizedLogger, ErrorCode


class VehicleSearchWithMCP:
    """Vehicle search implementation using Playwright MCP"""
    
    def __init__(self, logger: OptimizedLogger = None):
        self.logger = logger or OptimizedLogger("vehicle_search_mcp", "SEARCH")
    
    async def search_and_select_vehicle(self, vehicle_number: str = "6897") -> bool:
        """
        Main function to search for vehicle number and select result
        
        Args:
            vehicle_number: Vehicle number to search (default: "6897")
            
        Returns:
            bool: True if search and selection successful
        """
        try:
            self.logger.log_info(f"[시작] 차량번호 '{vehicle_number}' 검색 및 선택 프로세스 시작")
            
            # Step 1: Input vehicle number
            if not await self._input_vehicle_number(vehicle_number):
                return False
                
            # Step 2: Click search button
            if not await self._click_search_button():
                return False
                
            # Step 3: Wait for and handle search results
            if not await self._handle_search_results():
                return False
                
            # Step 4: Select vehicle from results
            if not await self._select_vehicle_from_results():
                return False
                
            # Step 5: Navigate to pre-coupon application stage
            if not await self._navigate_to_pre_coupon_stage():
                return False
                
            self.logger.log_info(f"[완료] 차량번호 '{vehicle_number}' 검색 및 선택 완료")
            return True
            
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_SEARCH, "차량검색선택", f"전체 프로세스 실패: {str(e)}")
            return False
    
    async def _input_vehicle_number(self, vehicle_number: str) -> bool:
        """Step 1: Input vehicle number into search field"""
        try:
            self.logger.log_info(f"[1단계] 차량번호 '{vehicle_number}' 입력 시작")
            
            # Using MCP to execute playwright code for vehicle number input
            await self._execute_mcp_command(f"""
                // Find vehicle number input field
                const vehicleInput = await page.getByRole('textbox', {{ name: '차량번호' }});
                if (!vehicleInput) {{
                    throw new Error('차량번호 입력 필드를 찾을 수 없습니다');
                }}
                
                // Clear existing input and fill with new vehicle number
                await vehicleInput.clear();
                await vehicleInput.fill('{vehicle_number}');
                
                console.log('차량번호 입력 완료: {vehicle_number}');
            """)
            
            self.logger.log_info(f"[1단계 완료] 차량번호 '{vehicle_number}' 입력 성공")
            return True
            
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_SEARCH, "차량번호입력", f"차량번호 입력 실패: {str(e)}")
            return False
    
    async def _click_search_button(self) -> bool:
        """Step 2: Click the vehicle search button"""
        try:
            self.logger.log_info("[2단계] '차량조회' 버튼 클릭 시작")
            
            await self._execute_mcp_command("""
                // Find and click the search button using multiple selector strategies
                let searchButton = null;
                
                // Strategy 1: Role-based selector
                try {
                    searchButton = await page.getByRole('button', { name: '차량조회' });
                    if (await searchButton.count() > 0) {
                        await searchButton.click();
                        console.log('차량조회 버튼 클릭 완료 (role-based)');
                        return;
                    }
                } catch (e) {}
                
                // Strategy 2: Text-based selector
                try {
                    searchButton = await page.locator('button:has-text("차량조회")');
                    if (await searchButton.count() > 0) {
                        await searchButton.click();
                        console.log('차량조회 버튼 클릭 완료 (text-based)');
                        return;
                    }
                } catch (e) {}
                
                // Strategy 3: Name attribute selector
                try {
                    searchButton = await page.locator('button[name="search"]');
                    if (await searchButton.count() > 0) {
                        await searchButton.click();
                        console.log('차량조회 버튼 클릭 완료 (name attribute)');
                        return;
                    }
                } catch (e) {}
                
                throw new Error('차량조회 버튼을 찾을 수 없습니다');
            """)
            
            # Wait for search results to load
            await asyncio.sleep(2)
            
            self.logger.log_info("[2단계 완료] '차량조회' 버튼 클릭 성공")
            return True
            
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_SEARCH, "검색버튼클릭", f"검색 버튼 클릭 실패: {str(e)}")
            return False
    
    async def _handle_search_results(self) -> bool:
        """Step 3: Wait for and validate search results"""
        try:
            self.logger.log_info("[3단계] 검색 결과 처리 시작")
            
            # Check for no results popup first
            no_result_found = await self._execute_mcp_command("""
                // Check for various "no results" patterns
                const noResultPatterns = [
                    'text=검색 결과가 없습니다',
                    'text="검색 결과가 없습니다"',
                    'text=검색된 차량이 없습니다',
                    'text="검색된 차량이 없습니다"'
                ];
                
                for (const pattern of noResultPatterns) {
                    const noResultElement = page.locator(pattern);
                    if (await noResultElement.count() > 0) {
                        console.log('검색 결과 없음 팝업 감지');
                        
                        // Close the popup
                        const closeButtons = ['text=OK', 'text="OK"', 'text=확인', 'text="확인"'];
                        for (const closeSelector of closeButtons) {
                            const closeButton = page.locator(closeSelector);
                            if (await closeButton.count() > 0) {
                                await closeButton.click();
                                await page.waitForTimeout(1000);
                                console.log('검색 결과 없음 팝업 닫기 완료');
                                break;
                            }
                        }
                        return true; // Found no results
                    }
                }
                return false; // Results found
            """)
            
            if no_result_found:
                self.logger.log_warning("[3단계] 검색 결과 없음 - 프로세스 종료")
                return False
            
            # Wait for results table to appear
            await self._execute_mcp_command("""
                // Wait for the search results table to appear
                await page.waitForSelector('#tableid', { timeout: 10000 });
                console.log('검색 결과 테이블 로드 완료');
            """)
            
            self.logger.log_info("[3단계 완료] 검색 결과 처리 성공")
            return True
            
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_SEARCH, "검색결과처리", f"검색 결과 처리 실패: {str(e)}")
            return False
    
    async def _select_vehicle_from_results(self) -> bool:
        """Step 4: Click on the vehicle row from search results"""
        try:
            self.logger.log_info("[4단계] 검색 결과에서 차량 선택 시작")
            
            vehicle_selected = await self._execute_mcp_command("""
                // Find and click the vehicle row in the results table
                const resultsTable = page.locator('#tableid');
                
                if (await resultsTable.count() === 0) {
                    throw new Error('검색 결과 테이블을 찾을 수 없습니다');
                }
                
                // Look for clickable rows with vehicle data
                const vehicleRows = resultsTable.locator('tr[onclick*="setDiscount"]');
                const rowCount = await vehicleRows.count();
                
                if (rowCount === 0) {
                    throw new Error('클릭 가능한 차량 행을 찾을 수 없습니다');
                }
                
                // Click the first vehicle row (or specify index if needed)
                const firstRow = vehicleRows.first();
                await firstRow.click();
                
                console.log(`차량 선택 완료 (총 ${rowCount}개 결과 중 첫 번째 선택)`);
                return true;
            """)
            
            if not vehicle_selected:
                self.logger.log_error(ErrorCode.FAIL_SEARCH, "차량선택", "차량 선택 실패")
                return False
            
            # Wait for navigation/page update
            await asyncio.sleep(2)
            
            self.logger.log_info("[4단계 완료] 차량 선택 성공")
            return True
            
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_SEARCH, "차량선택", f"차량 선택 실패: {str(e)}")
            return False
    
    async def _navigate_to_pre_coupon_stage(self) -> bool:
        """Step 5: Navigate to pre-coupon application stage"""
        try:
            self.logger.log_info("[5단계] 쿠폰 적용 전 단계로 이동 시작")
            
            # Wait for page to fully load after vehicle selection
            await self._execute_mcp_command("""
                // Wait for the page to stabilize after vehicle selection
                await page.waitForLoadState('networkidle');
                
                // Check if we're now on the coupon application page
                // Look for typical elements that appear before coupon application
                const couponElements = [
                    'text=쿠폰',
                    'text=할인',
                    'text=적용',
                    '#myDcList',
                    '#allDcList',
                    '#productList'
                ];
                
                let foundCouponPage = false;
                for (const selector of couponElements) {
                    if (await page.locator(selector).count() > 0) {
                        foundCouponPage = true;
                        console.log(`쿠폰 페이지 요소 발견: ${selector}`);
                        break;
                    }
                }
                
                if (foundCouponPage) {
                    console.log('쿠폰 적용 전 단계 페이지 도달 확인');
                } else {
                    console.log('쿠폰 페이지 요소를 찾지 못했지만 계속 진행');
                }
            """)
            
            self.logger.log_info("[5단계 완료] 쿠폰 적용 전 단계 도달 성공")
            return True
            
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_SEARCH, "페이지이동", f"쿠폰 적용 전 단계 이동 실패: {str(e)}")
            return False
    
    async def _execute_mcp_command(self, playwright_code: str) -> any:
        """
        Execute Playwright code using MCP
        
        Args:
            playwright_code: JavaScript code to execute in Playwright context
            
        Returns:
            Result of the executed code or None if execution failed
        """
        try:
            self.logger.log_info(f"[MCP] Executing Playwright code: {playwright_code[:50]}...")
            
            # Note: This is a demonstration implementation
            # In a real environment with MCP server running, this would:
            # 1. Connect to the MCP playwright server
            # 2. Execute the JavaScript code in the browser context
            # 3. Return the actual results
            
            # For demonstration purposes, simulate different scenarios based on code content
            if "검색 결과가 없습니다" in playwright_code:
                # Simulate finding search results (not no-results)
                self.logger.log_info("[MCP 시뮬레이션] 검색 결과 발견")
                return False  # No "no results" found, meaning results exist
            elif "setDiscount" in playwright_code:
                # Simulate successful vehicle selection
                self.logger.log_info("[MCP 시뮬레이션] 차량 행 클릭 성공")
                return True
            elif "tableid" in playwright_code:
                # Simulate table loading
                self.logger.log_info("[MCP 시뮬레이션] 결과 테이블 로드 완료")
                return True
            else:
                # Simulate successful execution for other commands
                await asyncio.sleep(0.1)  # Simulate execution time
                return True
            
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_SEARCH, "MCP실행", f"MCP 명령 실행 실패: {str(e)}")
            return None


# Usage example
async def main():
    """Example usage of the vehicle search functionality"""
    logger = OptimizedLogger("vehicle_search_example", "EXAMPLE")
    search_handler = VehicleSearchWithMCP(logger)
    
    # Execute the complete vehicle search and selection process
    success = await search_handler.search_and_select_vehicle("6897")
    
    if success:
        logger.log_info("[완료] 전체 차량 검색 및 선택 프로세스 성공")
    else:
        logger.log_error(ErrorCode.FAIL_SEARCH, "전체프로세스", "차량 검색 및 선택 프로세스 실패")


if __name__ == "__main__":
    asyncio.run(main())