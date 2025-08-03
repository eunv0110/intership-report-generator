from collections import defaultdict
from typing import Dict, List, Any
from src.client import NotionClient
from src.renderers import NotionPageFormatter, NotionBlockRenderer
from src.date_utils import DateUtils
from src.exceptions import NotionAPIError


class WeeklyManager:
    """주차별 페이지 관리 클래스"""

    def __init__(self, client: NotionClient):
        self.client = client
        self.weekly_pages = defaultdict(list)  # {week_number: [pages]}

    def analyze_pages_by_week(
        self, pages: List[Dict[str, Any]]
    ) -> Dict[int, List[Dict[str, Any]]]:
        """페이지들을 주차별로 분석하여 그룹화"""
        self.weekly_pages.clear()

        for page in pages:
            # 페이지에서 날짜 찾기
            page_date = NotionPageFormatter.get_page_date(page["properties"])
            if page_date:
                korean_date, week_num = DateUtils.get_date_info(page_date)

                # 페이지에 날짜 정보 추가
                page["_date_info"] = {
                    "original_date": page_date,
                    "korean_date": korean_date,
                    "week_number": week_num,
                }

                self.weekly_pages[week_num].append(page)

        return dict(self.weekly_pages)

    def print_weekly_summary(self):
        """주차별 요약 출력"""
        if not self.weekly_pages:
            print("📭 분석된 페이지가 없습니다.")
            return

        print("\n" + "=" * 60)
        print("📅 주차별 페이지 요약")
        print("=" * 60)

        for week_num in sorted(self.weekly_pages.keys()):
            pages = self.weekly_pages[week_num]
            print(f"\n🗓️  {week_num}주차 ({len(pages)}개 페이지)")

            for page in pages[:3]:  # 최대 3개만 미리보기
                title = (
                    NotionPageFormatter.format_property_value(
                        next(
                            (
                                prop
                                for prop in page["properties"].values()
                                if prop.get("type") == "title"
                            ),
                            {},
                        )
                    )
                    or "제목 없음"
                )

                date_info = page.get("_date_info", {})
                korean_date = date_info.get("korean_date", "날짜 없음")

                print(f"    • {korean_date}: {title}")

            if len(pages) > 3:
                print(f"    ... 외 {len(pages) - 3}개")

    def print_week_details(self, week_number: int):
        """특정 주차의 상세 정보 출력"""
        if week_number not in self.weekly_pages:
            print(f"❌ {week_number}주차에 해당하는 페이지가 없습니다.")
            return

        pages = self.weekly_pages[week_number]
        print(f"\n" + "=" * 60)
        print(f"📋 {week_number}주차 상세 정보 ({len(pages)}개 페이지)")
        print("=" * 60)

        for i, page in enumerate(pages, 1):
            date_info = page.get("_date_info", {})
            korean_date = date_info.get("korean_date", "날짜 없음")

            title = (
                NotionPageFormatter.format_property_value(
                    next(
                        (
                            prop
                            for prop in page["properties"].values()
                            if prop.get("type") == "title"
                        ),
                        {},
                    )
                )
                or "제목 없음"
            )

            print(f"\n📄 {i}. {korean_date} - {title}")
            print("-" * 50)

            # 본문 내용 가져오기
            try:
                blocks_tree = self.client.get_block_tree(page["id"])
                if blocks_tree:
                    content = NotionBlockRenderer.render_blocks(blocks_tree)
                    if content.strip():
                        print(content)
                    else:
                        print("📄 내용이 비어있습니다.")
                else:
                    print("📄 내용이 비어있습니다.")
            except NotionAPIError as e:
                print(f"❌ 내용을 가져올 수 없습니다: {e}")

    def get_available_weeks(self) -> List[int]:
        """사용 가능한 주차 목록 반환"""
        return sorted(self.weekly_pages.keys())
