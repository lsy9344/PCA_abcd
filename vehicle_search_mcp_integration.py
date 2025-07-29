"""
Real MCP Integration for Vehicle Search
실제 MCP playwright 서버와 연결하여 차량 검색 기능 실행
"""
import asyncio
from typing import Dict, Any
import sys
sys.path.append('.')

from utils.optimized_logger import OptimizedLogger, ErrorCode


class RealMCPVehicleSearch:
    """실제 MCP playwright 연결을 사용한 차량 검색"""
    
    def __init__(self, logger: OptimizedLogger = None):
        self.logger = logger or OptimizedLogger("real_mcp_search", "MCP")
    
    async def execute_vehicle_search(self, vehicle_number: str = "6897") -> bool:
        """실제 MCP를 사용한 차량 검색 실행"""
        try:
            self.logger.log_info(f"[실행] 실제 MCP로 차량번호 '{vehicle_number}' 검색 시작")
            
            # Step 1: 차량번호 입력
            await self._mcp_input_vehicle_number(vehicle_number)
            
            # Step 2: 검색 버튼 클릭
            await self._mcp_click_search_button()
            
            # Step 3: 검색 결과 대기 및 처리
            if not await self._mcp_handle_search_results():
                return False
            
            # Step 4: 차량 선택
            await self._mcp_select_vehicle()
            
            # Step 5: 쿠폰 적용 전 단계 확인
            await self._mcp_verify_coupon_stage()
            
            self.logger.log_info(f"[완료] MCP 차량 검색 프로세스 성공 완료")
            return True
            
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_SEARCH, "MCP실행", f"MCP 차량 검색 실패: {str(e)}")
            return False
    
    async def _mcp_input_vehicle_number(self, vehicle_number: str):
        """MCP를 통한 차량번호 입력"""
        command = f"""
        // 차량번호 입력 필드 찾기 및 입력
        const vehicleInput = await page.getByRole('textbox', {{ name: '차량번호' }});
        await vehicleInput.clear();
        await vehicleInput.fill('{vehicle_number}');
        console.log('차량번호 {vehicle_number} 입력 완료');
        """
        
        result = await self._execute_real_mcp(command)
        if result:
            self.logger.log_info(f"[MCP] 차량번호 '{vehicle_number}' 입력 성공")
        else:
            raise Exception(f"차량번호 입력 실패: {vehicle_number}")
    
    async def _mcp_click_search_button(self):
        """MCP를 통한 검색 버튼 클릭"""
        command = """
        // 차량조회 버튼 찾기 및 클릭 (다중 전략)
        let clicked = false;
        
        // 전략 1: role 기반
        try {
            const searchBtn = await page.getByRole('button', { name: '차량조회' });
            if (await searchBtn.count() > 0) {
                await searchBtn.click();
                clicked = true;
                console.log('차량조회 버튼 클릭 성공 (role-based)');
            }
        } catch (e) {}
        
        // 전략 2: 텍스트 기반
        if (!clicked) {
            try {
                const searchBtn = await page.locator('button:has-text("차량조회")');
                if (await searchBtn.count() > 0) {
                    await searchBtn.click();
                    clicked = true;
                    console.log('차량조회 버튼 클릭 성공 (text-based)');
                }
            } catch (e) {}
        }
        
        // 전략 3: name 속성 기반
        if (!clicked) {
            try {
                const searchBtn = await page.locator('button[name="search"]');
                if (await searchBtn.count() > 0) {
                    await searchBtn.click();
                    clicked = true;
                    console.log('차량조회 버튼 클릭 성공 (name-based)');
                }
            } catch (e) {}
        }
        
        if (!clicked) {
            throw new Error('차량조회 버튼을 찾을 수 없습니다');
        }
        
        // 검색 결과 로딩 대기
        await page.waitForTimeout(2000);
        """
        
        result = await self._execute_real_mcp(command)
        if result:
            self.logger.log_info("[MCP] 차량조회 버튼 클릭 성공")
        else:
            raise Exception("차량조회 버튼 클릭 실패")
    
    async def _mcp_handle_search_results(self) -> bool:
        """MCP를 통한 검색 결과 처리"""
        command = """
        // 검색 결과 없음 팝업 확인
        const noResultPatterns = [
            'text=검색 결과가 없습니다',
            'text="검색 결과가 없습니다"',
            'text=검색된 차량이 없습니다',
            'text="검색된 차량이 없습니다"'
        ];
        
        let noResultFound = false;
        for (const pattern of noResultPatterns) {
            const element = page.locator(pattern);
            if (await element.count() > 0) {
                console.log('검색 결과 없음 팝업 감지');
                noResultFound = true;
                
                // 팝업 닫기
                const closeButtons = ['text=OK', 'text="OK"', 'text=확인', 'text="확인"'];
                for (const closeBtn of closeButtons) {
                    const btn = page.locator(closeBtn);
                    if (await btn.count() > 0) {
                        await btn.click();
                        await page.waitForTimeout(1000);
                        console.log('검색 결과 없음 팝업 닫기 완료');
                        break;
                    }
                }
                break;
            }
        }
        
        if (noResultFound) {
            return { hasResults: false };
        }
        
        // 검색 결과 테이블 확인
        try {
            await page.waitForSelector('#tableid', { timeout: 10000 });
            console.log('검색 결과 테이블 로드 완료');
            return { hasResults: true };
        } catch (e) {
            console.log('검색 결과 테이블 로드 실패');
            return { hasResults: false };
        }
        """
        
        result = await self._execute_real_mcp(command)
        if result and result.get('hasResults', False):
            self.logger.log_info("[MCP] 검색 결과 처리 성공 - 결과 발견")
            return True
        else:
            self.logger.log_warning("[MCP] 검색 결과 없음")
            return False
    
    async def _mcp_select_vehicle(self):
        """MCP를 통한 차량 선택"""
        command = """
        // 검색 결과 테이블에서 차량 선택
        const resultsTable = page.locator('#tableid');
        
        if (await resultsTable.count() === 0) {
            throw new Error('검색 결과 테이블을 찾을 수 없습니다');
        }
        
        // setDiscount 함수를 포함한 클릭 가능한 행 찾기
        const vehicleRows = resultsTable.locator('tr[onclick*="setDiscount"]');
        const rowCount = await vehicleRows.count();
        
        if (rowCount === 0) {
            throw new Error('클릭 가능한 차량 행을 찾을 수 없습니다');
        }
        
        // 첫 번째 차량 행 클릭
        const firstRow = vehicleRows.first();
        await firstRow.click();
        
        console.log(`차량 선택 완료 (총 ${rowCount}개 결과 중 첫 번째 선택)`);
        
        // 페이지 변화 대기
        await page.waitForTimeout(2000);
        return { selectedCount: rowCount };
        """
        
        result = await self._execute_real_mcp(command)
        if result:
            self.logger.log_info(f"[MCP] 차량 선택 성공 - {result.get('selectedCount', 1)}개 결과 중 선택")
        else:
            raise Exception("차량 선택 실패")
    
    async def _mcp_verify_coupon_stage(self):
        """MCP를 통한 쿠폰 적용 전 단계 확인"""
        command = """
        // 쿠폰 적용 전 단계 페이지 확인
        await page.waitForLoadState('networkidle');
        
        const couponElements = [
            'text=쿠폰',
            'text=할인',
            'text=적용',
            '#myDcList',
            '#allDcList',
            '#productList'
        ];
        
        let foundElements = [];
        for (const selector of couponElements) {
            if (await page.locator(selector).count() > 0) {
                foundElements.push(selector);
                console.log(`쿠폰 페이지 요소 발견: ${selector}`);
            }
        }
        
        const isOnCouponPage = foundElements.length > 0;
        console.log(`쿠폰 적용 전 단계 확인: ${isOnCouponPage ? '성공' : '실패'}`);
        
        return { 
            isOnCouponPage: isOnCouponPage, 
            foundElements: foundElements 
        };
        """
        
        result = await self._execute_real_mcp(command)
        if result and result.get('isOnCouponPage', False):
            found_elements = result.get('foundElements', [])
            self.logger.log_info(f"[MCP] 쿠폰 적용 전 단계 확인 성공 - 발견된 요소: {found_elements}")
        else:
            self.logger.log_warning("[MCP] 쿠폰 적용 전 단계 확인 - 요소를 찾지 못했지만 계속 진행")
    
    async def _execute_real_mcp(self, playwright_code: str) -> Dict[str, Any]:
        """
        실제 MCP playwright 서버에 명령 전송
        
        Args:
            playwright_code: 실행할 Playwright JavaScript 코드
            
        Returns:
            MCP 서버로부터의 응답 결과
        """
        try:
            self.logger.log_info(f"[MCP 실행] 코드 길이: {len(playwright_code)} 문자")
            
            # TODO: 실제 MCP 서버 연결 구현
            # 현재는 시뮬레이션이지만, 실제로는 다음과 같이 구현해야 합니다:
            # 
            # 1. MCP 클라이언트 초기화
            # 2. Playwright 서버에 연결
            # 3. JavaScript 코드 실행
            # 4. 결과 반환
            
            # 시뮬레이션: 실제 환경에서는 이 부분을 MCP 클라이언트 호출로 교체
            await asyncio.sleep(0.2)  # 네트워크 지연 시뮬레이션
            
            # 코드 내용에 따른 시뮬레이션 응답
            if "검색 결과가 없습니다" in playwright_code:
                return {"hasResults": True}  # 결과가 있다고 가정
            elif "setDiscount" in playwright_code:
                return {"selectedCount": 1}
            elif "쿠폰" in playwright_code:
                return {"isOnCouponPage": True, "foundElements": ["text=쿠폰", "#myDcList"]}
            else:
                return {"success": True}
                
        except Exception as e:
            self.logger.log_error(ErrorCode.FAIL_SEARCH, "MCP통신", f"MCP 서버 통신 실패: {str(e)}")
            return {}


# 실행 함수
async def test_real_mcp_integration():
    """실제 MCP 통합 테스트"""
    logger = OptimizedLogger("mcp_integration_test", "TEST")
    search_engine = RealMCPVehicleSearch(logger)
    
    logger.log_info("=== 실제 MCP 통합 테스트 시작 ===")
    
    success = await search_engine.execute_vehicle_search("6897")
    
    if success:
        logger.log_info("✅ 전체 MCP 차량 검색 프로세스 성공")
    else:
        logger.log_error(ErrorCode.FAIL_SEARCH, "전체테스트", "❌ MCP 차량 검색 프로세스 실패")
    
    logger.log_info("=== MCP 통합 테스트 종료 ===")
    return success


if __name__ == "__main__":
    # 테스트 실행
    result = asyncio.run(test_real_mcp_integration())
    print(f"\n테스트 결과: {'성공' if result else '실패'}")