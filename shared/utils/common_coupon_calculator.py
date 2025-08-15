"""
공통 쿠폰 계산 유틸리티
모든 매장에서 사용할 수 있는 현재 적용 쿠폰 파싱 및 계산 로직
"""
from typing import Dict, Tuple, List
from playwright.async_api import Page


class CommonCouponCalculator:
    """매장 간 공통 쿠폰 계산 로직"""
    
    @staticmethod
    async def parse_applied_coupons(
        page: Page, 
        coupon_key_mapping: Dict[str, str],
        discount_selectors: List[str],
        has_my_history: bool = True
    ) -> Tuple[Dict[str, int], Dict[str, int]]:
        """
        현재 적용된 쿠폰 파싱 (모든 매장 공통)
        
        Args:
            page: Playwright 페이지 객체
            coupon_key_mapping: 쿠폰 이름 -> 키 매핑 딕셔너리
            discount_selectors: 할인 내역 테이블 셀렉터 리스트
            
        Returns:
            (my_history, total_history) 튜플
        """
        my_history = {}
        total_history = {}
        
        print(f"   🔍 현재 적용된 쿠폰 파싱 시작...")
        
        # 페이지에서 사용 가능한 모든 테이블 확인
        try:
            all_tables = await page.locator('table').all()
            all_tbodies = await page.locator('tbody').all()
            print(f"     🔍 페이지 내 총 테이블 수: {len(all_tables)}개")
            print(f"     🔍 페이지 내 총 tbody 수: {len(all_tbodies)}개")
            
            # tbody id/name 속성 확인
            for i, tbody in enumerate(all_tbodies):
                try:
                    id_attr = await tbody.get_attribute('id')
                    name_attr = await tbody.get_attribute('name')
                    class_attr = await tbody.get_attribute('class')
                    print(f"     🔍 tbody {i+1}: id='{id_attr}', name='{name_attr}', class='{class_attr}'")
                except:
                    pass
        except Exception as e:
            print(f"     ⚠️ 페이지 구조 분석 오류: {str(e)}")
        
        for selector in discount_selectors:
            try:
                print(f"     🎯 셀렉터 시도: {selector}")
                rows = await page.locator(selector).all()
                print(f"     📊 발견된 행 수: {len(rows)}개")
                
                if len(rows) > 0:
                    print(f"     📊 할인 내역 테이블 발견: {selector} ({len(rows)}개 행)")
                    
                    for row_idx, row in enumerate(rows):
                        try:
                            # 각 행의 셀들 가져오기
                            cells = await row.locator('td').all()
                            
                            if len(cells) >= 4:  # C 매장: 최소 4개 셀 필요 (빈값, 날짜, 할인권명, 수량)
                                # 셀 내용 추출
                                cell_texts = []
                                for cell in cells:
                                    cell_text = await cell.inner_text()
                                    cell_texts.append(cell_text.strip())
                                
                                print(f"     📝 행 {row_idx + 1}: {' | '.join(cell_texts[:5])}")  # 처음 5개 셀 출력
                                
                                # C 매장 구조: 3번째 셀(인덱스 2) = 할인권명, 4번째 셀(인덱스 3) = 수량
                                if len(cell_texts) >= 4:
                                    coupon_cell = cell_texts[2]  # 3번째 셀 (할인권명)
                                    quantity_cell = cell_texts[3]  # 4번째 셀 (수량)
                                    
                                    # 쿠폰 이름 매핑 확인
                                    for mapped_name, coupon_key in coupon_key_mapping.items():
                                        if mapped_name in coupon_cell:
                                            # 수량 숫자 추출 ("1매" -> 1)
                                            import re
                                            quantity_match = re.search(r'(\d+)', quantity_cell)
                                            quantity = int(quantity_match.group(1)) if quantity_match else 1
                                            
                                            # C 매장은 total_history만 사용
                                            if has_my_history:
                                                my_history[coupon_key] = my_history.get(coupon_key, 0) + quantity
                                            total_history[coupon_key] = total_history.get(coupon_key, 0) + quantity
                                            
                                            print(f"     ✅ 적용된 쿠폰 발견: {mapped_name} {quantity}개 -> {coupon_key}")
                                            break
                                        
                        except Exception as e:
                            print(f"     ⚠️ 행 파싱 오류: {str(e)}")
                            continue
                    break
                    
            except Exception as e:
                print(f"     ⚠️ 테이블 파싱 오류: {str(e)}")
                continue
        
        # 파싱 결과 출력
        if my_history or total_history:
            print(f"   📊 현재 적용된 쿠폰 내역:")
            print(f"     - 매장 내역: {my_history}")
            print(f"     - 전체 내역: {total_history}")
        else:
            print(f"   📊 현재 적용된 쿠폰 없음 (새로 적용 가능)")
        
        return my_history, total_history

    @staticmethod
    def calculate_remaining_minutes(
        target_minutes: int,
        coupon_durations: Dict[str, int],
        current_history: Dict[str, int]
    ) -> int:
        """
        현재 적용된 쿠폰을 고려한 남은 할인 시간 계산
        
        Args:
            target_minutes: 목표 할인 시간 (분)
            coupon_durations: 쿠폰별 할인 시간 (분) 매핑
            current_history: 현재 적용된 쿠폰 내역
            
        Returns:
            남은 할인 시간 (분)
        """
        current_minutes = 0
        
        for coupon_key, count in current_history.items():
            if coupon_key in coupon_durations:
                current_minutes += count * coupon_durations[coupon_key]
        
        remaining_minutes = max(0, target_minutes - current_minutes)
        
        print(f"   📊 현재 적용된 할인: {current_minutes}분")
        print(f"   📊 추가 필요 할인: {remaining_minutes}분")
        
        return remaining_minutes

    @staticmethod
    def should_apply_free_coupon(
        total_free_used: int,
        current_free: int,
        remaining_minutes: int,
        free_coupon_duration: int
    ) -> bool:
        """
        무료 쿠폰 적용 여부 결정 (공통 로직)
        
        Args:
            total_free_used: 전체 매장에서 사용한 무료 쿠폰 수
            current_free: 현재 적용된 무료 쿠폰 수
            remaining_minutes: 남은 할인 시간
            free_coupon_duration: 무료 쿠폰 할인 시간 (분)
            
        Returns:
            무료 쿠폰 적용 가능 여부
        """
        return (
            total_free_used == 0 and  # 전체 매장에서 사용 이력 없음
            current_free == 0 and    # 현재 적용된 무료 쿠폰 없음
            remaining_minutes >= free_coupon_duration  # 충분한 시간 필요
        )

    @staticmethod
    def format_coupon_display_name(coupon_key: str) -> str:
        """쿠폰 키를 표시용 이름으로 변환"""
        return (coupon_key
                .replace("_", " ")
                .replace("FREE", "무료")
                .replace("PAID", "유료") 
                .replace("1HOUR", "1시간")
                .replace("2HOUR", "2시간"))


# 매장별 설정 클래스 - DEPRECATED
class StoreConfig:
    """
    매장별 쿠폰 설정 - DEPRECATED
    
    ⚠️ 이 클래스는 더 이상 사용되지 않습니다.
    대신 infrastructure/config/config_manager.py의 ConfigManager를 사용하세요.
    YAML 파일 기반 설정으로 완전히 이관되었습니다.
    """
    
    @staticmethod
    def get_coupon_config(store_id: str) -> Dict:
        """
        매장별 쿠폰 설정 반환 - DEPRECATED
        
        ⚠️ 이 메서드는 더 이상 사용되지 않습니다.
        대신 YAML 설정 파일을 직접 사용하세요:
        
        # 올바른 사용법:
        from pathlib import Path
        import yaml
        
        config_path = Path("infrastructure/config/store_configs/{store_id.lower()}_store_config.yaml")
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        """
        import warnings
        warnings.warn(
            "StoreConfig.get_coupon_config()는 deprecated됩니다. "
            "대신 YAML 설정 파일을 직접 사용하세요.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # 기존 하드코딩된 설정 (하위 호환성을 위해 유지)
        configs = {
            "A": {
                "coupon_key_mapping": {
                    "30분할인권(무료)": "FREE_COUPON",
                    "1시간할인권(유료)": "PAID_COUPON",
                    "1시간주말할인권(유료)": "WEEKEND_COUPON"
                },
                "coupon_durations": {
                    "FREE_COUPON": 60,
                    "PAID_COUPON": 60,
                    "WEEKEND_COUPON": 60
                },
                "discount_selectors": ["#myDcList tr", "#allDcList tr"]
            },
            "B": {
                "coupon_key_mapping": {
                    "무료 1시간할인": "FREE_COUPON",
                    "유료 30분할인": "PAID_COUPON"
                },
                "coupon_durations": {
                    "FREE_COUPON": 60,
                    "PAID_COUPON": 30
                },
                "discount_selectors": [".discount-list tr", "#discountHistory tr"]
            },
            "C": {
                "coupon_key_mapping": {
                    "2시간 무료할인권": "FREE_2HOUR",
                    "무료 2시간할인": "FREE_2HOUR", 
                    "1시간 유료할인권": "PAID_1HOUR",
                    "유료할인권": "PAID_1HOUR",
                    "유료할인": "PAID_1HOUR"
                },
                "coupon_durations": {
                    "FREE_2HOUR": 120,
                    "PAID_1HOUR": 60
                },
                "discount_selectors": [
                    "tbody[id='discountlist'] tr"
                ],
                "has_my_history": False  # C 매장은 my_history가 없음
            }
        }
        
        return configs.get(store_id.upper(), configs["C"])  # 기본값은 C 매장 