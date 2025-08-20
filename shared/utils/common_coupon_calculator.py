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
        
        
        # 페이지에서 사용 가능한 모든 테이블 확인
        try:
            all_tables = await page.locator('table').all()
            all_tbodies = await page.locator('tbody').all()
            
            # tbody id/name 속성 확인
            for i, tbody in enumerate(all_tbodies):
                try:
                    id_attr = await tbody.get_attribute('id')
                    name_attr = await tbody.get_attribute('name')
                    class_attr = await tbody.get_attribute('class')
                except:
                    pass
        except Exception as e:
        
        # 모든 셀렉터를 하나로 합쳐서 모든 행을 가져오기 (B 매장의 경우 ev_ 와 odd_ 모두 필요)
        all_rows = []
        all_selector = ", ".join(discount_selectors)
        
        try:
            all_rows = await page.locator(all_selector).all()
            
            if len(all_rows) > 0:
                
                for row_idx, row in enumerate(all_rows):
                    try:
                        # 각 행의 셀들 가져오기
                        cells = await row.locator('td').all()
                        
                        if len(cells) >= 3:  # A매장은 3개 셀, B/C매장은 4개 셀
                                # 셀 내용 추출
                                cell_texts = []
                                for cell in cells:
                                    cell_text = await cell.inner_text()
                                    cell_texts.append(cell_text.strip())
                                
                                
                                # 매장별 데이터 구조 처리
                                if len(cell_texts) >= 3:
                                    # A매장 구조: 날짜(0) | 할인권명(1) | 수량(2)
                                    # B매장 구조: 번호(0) | 할인값(1) | 등록자(2) | 등록일(3)
                                    # C매장 구조: 빈값(0) | 날짜(1) | 할인권명(2) | 수량(3)
                                    
                                    coupon_cell = None
                                    quantity = 1  # 기본값
                                    
                                    # A매장 패턴: 3개 셀이고 1번째 셀(인덱스 0)에 "30분할인권(무료)", "1시간할인권(유료)" 등이 있음
                                    if len(cell_texts) == 3 and any(pattern in cell_texts[0] for pattern in ["30분할인권(무료)", "1시간할인권(유료)", "1시간주말할인권(유료)"]):
                                        coupon_cell = cell_texts[0]  # A매장: 1번째 셀 (할인권명)
                                        quantity_cell = cell_texts[1]  # A매장: 2번째 셀 (수량)
                                        # 수량 숫자 추출 ("1회" -> 1)
                                        import re
                                        quantity_match = re.search(r'(\d+)', quantity_cell)
                                        quantity = int(quantity_match.group(1)) if quantity_match else 1
                                    
                                    # B매장 패턴: 2번째 셀에 쿠폰명이 있고, 차량 정보 행이 아닌 경우
                                    elif len(cell_texts) >= 4:
                                        # B매장 쿠폰 행인지 정확히 판단
                                        second_cell = cell_texts[1].strip()
                                        is_coupon_row = False
                                        
                                        # 정확한 쿠폰명 매칭
                                        if second_cell in ["무료 1시간할인", "유료 30분할인"]:
                                            is_coupon_row = True
                                        # 부분 매칭 (혹시 추가 텍스트가 있을 경우)
                                        elif ("무료" in second_cell and "시간할인" in second_cell) or ("유료" in second_cell and "분할인" in second_cell):
                                            is_coupon_row = True
                                        
                                        # 차량 정보 행 제외 (차량번호가 포함된 행, 숫자만 있는 행, 날짜만 있는 행)
                                        if "다" in second_cell or "차" in second_cell:  # 차량번호 패턴 (38다4603)
                                            is_coupon_row = False
                                        elif second_cell.isdigit():  # 숫자만 있는 경우
                                            is_coupon_row = False
                                        elif len(second_cell) > 20:  # 너무 긴 텍스트 (차량 정보일 가능성)
                                            is_coupon_row = False
                                        
                                        if is_coupon_row:
                                            coupon_cell = second_cell
                                            quantity = 1  # B매장은 항상 1개씩
                                        else:
                                            coupon_cell = None
                                    
                                    # C매장 패턴: 4개 셀이고 3번째 칼럼에 할인권명이 있음
                                    elif len(cell_texts) >= 4 and any(name in cell_texts[2] for name in ["무료", "유료", "할인권"]):
                                        coupon_cell = cell_texts[2]  # C매장: 3번째 셀 (할인권명)
                                        quantity_cell = cell_texts[3]  # C매장: 4번째 셀 (수량)
                                        # 수량 숫자 추출 ("1매" -> 1)
                                        import re
                                        quantity_match = re.search(r'(\d+)', quantity_cell)
                                        quantity = int(quantity_match.group(1)) if quantity_match else 1
                                    
                                    if coupon_cell:
                                        # 쿠폰 이름 매핑 확인
                                        for mapped_name, coupon_key in coupon_key_mapping.items():
                                            if mapped_name in coupon_cell:
                                                # 적용된 쿠폰 카운트
                                                if has_my_history:
                                                    my_history[coupon_key] = my_history.get(coupon_key, 0) + quantity
                                                total_history[coupon_key] = total_history.get(coupon_key, 0) + quantity
                                                
                                                break
                                        
                    except Exception as e:
                        continue
                        
        except Exception as e:
            # 실패하면 기존 방식으로 fallback
            for selector in discount_selectors:
                try:
                    rows = await page.locator(selector).all()
                    
                    if len(rows) > 0:
                        # 기존 파싱 로직과 동일하게 처리
                        break
                        
                except Exception as e:
                    continue
        
        # 파싱 결과 출력
        if my_history or total_history:
            else:
        
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
                    "무료 1시간할인": "FREE_1HOUR",
                    "유료 30분할인": "PAID_30MIN"
                },
                "coupon_durations": {
                    "FREE_1HOUR": 60,
                    "PAID_30MIN": 30
                },
                "discount_selectors": [
                    "tr.ev_dhx_skyblue",
                    "tr.odd_dhx_skyblue",
                    ".gridbox tr",
                    "#gridbox tr"
                ]
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