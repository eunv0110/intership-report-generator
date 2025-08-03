from datetime import datetime, date
from typing import Optional
import calendar


class DateUtils:
    """날짜 관련 유틸리티 클래스"""

    @staticmethod
    def parse_notion_date(date_str: str) -> Optional[date]:
        """Notion 날짜 문자열을 파싱"""
        if not date_str:
            return None
        try:
            # "2025-08-01" 형식
            return datetime.strptime(date_str.split("T")[0], "%Y-%m-%d").date()
        except (ValueError, AttributeError):
            return None

    @staticmethod
    def get_week_number(target_date: date) -> int:
        """해당 월에서 몇 주차인지 계산 (월요일 시작)"""
        # 해당 월의 첫 번째 날
        first_day = target_date.replace(day=1)

        # 첫 번째 월요일 찾기
        first_monday = first_day
        while first_monday.weekday() != 0:  # 0 = 월요일
            first_monday = first_monday.replace(day=first_monday.day + 1)
            if first_monday.month != target_date.month:
                # 첫 번째 월요일이 다음 달로 넘어간 경우
                first_monday = first_day
                break

        # 타겟 날짜가 첫 번째 월요일보다 이전인 경우 1주차
        if target_date < first_monday:
            return 1

        # 주차 계산
        days_diff = (target_date - first_monday).days
        return (days_diff // 7) + 1

    @staticmethod
    def format_korean_date(target_date: date) -> str:
        """한국어 날짜 형식으로 포맷 (예: "8월 1일")"""
        return f"{target_date.month}월 {target_date.day}일"

    @staticmethod
    def get_date_info(date_str: str) -> tuple[str, int]:
        """날짜 문자열을 받아서 "몇월 몇일, 몇주차" 정보 반환"""
        parsed_date = DateUtils.parse_notion_date(date_str)
        if not parsed_date:
            return "날짜 없음", 0

        korean_date = DateUtils.format_korean_date(parsed_date)
        week_num = DateUtils.get_week_number(parsed_date)

        return korean_date, week_num
