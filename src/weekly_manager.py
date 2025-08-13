# src/weekly_manager.py
from collections import defaultdict
from typing import Dict, List, Any
from src.client import NotionClient
from src.renderers import NotionPageFormatter, NotionBlockRenderer
from src.date_utils import DateUtils
from src.exceptions import NotionAPIError
from src.ai_summarizer import ReportSummarizer
from src.report_generator import WeeklyReportGenerator


class WeeklyManager:
    """주차별 페이지 관리 클래스"""

    def __init__(
        self,
        client: NotionClient,
        summarizer: ReportSummarizer = None,
        week_calculation_method: str = "project",
    ):
        """
        Args:
            client: NotionClient 인스턴스
            summarizer: ReportSummarizer 인스턴스
            week_calculation_method: 주차 계산 방식 ("project", "monthly", "iso")
        """
        self.client = client
        self.weekly_pages = defaultdict(list)  # {week_number: [pages]}
        self.summarizer = summarizer
        self.report_generator = WeeklyReportGenerator()
        self.week_calculation_method = week_calculation_method

        print(f"📅 주차 계산 방식: {self._get_calculation_method_description()}")

    def _get_calculation_method_description(self) -> str:
        """주차 계산 방식 설명 반환"""
        descriptions = {
            "project": "프로젝트 기준 (연속 주차)",
            "monthly": "월별 기준 (매월 1주차부터)",
            "iso": "ISO 8601 기준 (국제 표준)",
        }
        return descriptions.get(self.week_calculation_method, "알 수 없음")

    def analyze_pages_by_week(
        self, pages: List[Dict[str, Any]]
    ) -> Dict[int, List[Dict[str, Any]]]:
        """페이지들을 주차별로 분석하여 그룹화"""
        self.weekly_pages.clear()

        for page in pages:
            # 페이지에서 날짜 찾기
            page_date = NotionPageFormatter.get_page_date(page["properties"])
            if page_date:
                korean_date, week_num = DateUtils.get_date_info(
                    page_date, self.week_calculation_method
                )

                # 주차 요약 정보 가져오기 (프로젝트 기준인 경우에만)
                week_summary = None
                if self.week_calculation_method == "project":
                    week_summary = DateUtils.get_week_summary(week_num)

                # 페이지에 날짜 정보 추가
                page["_date_info"] = {
                    "original_date": page_date,
                    "korean_date": korean_date,
                    "week_number": week_num,
                    "week_summary": week_summary,
                }

                self.weekly_pages[week_num].append(page)

        return dict(self.weekly_pages)

    def print_weekly_summary(self):
        """주차별 요약 출력"""
        if not self.weekly_pages:
            print("📭 분석된 페이지가 없습니다.")
            return

        print("\n" + "=" * 60)
        print(f"📅 주차별 페이지 요약 ({self._get_calculation_method_description()})")
        print("=" * 60)

        for week_num in sorted(self.weekly_pages.keys()):
            pages = self.weekly_pages[week_num]

            # 주차 정보 출력
            week_info = f"{week_num}주차 ({len(pages)}개 페이지)"
            if self.week_calculation_method == "project" and pages:
                week_summary = pages[0]["_date_info"].get("week_summary")
                if week_summary:
                    week_info += f" - {week_summary['korean_range']}"

            print(f"\n🗓️  {week_info}")

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

    def set_week_calculation_method(self, method: str):
        """주차 계산 방식 변경"""
        valid_methods = ["project", "monthly", "iso"]
        if method not in valid_methods:
            raise ValueError(
                f"유효하지 않은 계산 방식: {method}. 사용 가능: {valid_methods}"
            )

        self.week_calculation_method = method
        print(
            f"📅 주차 계산 방식이 '{self._get_calculation_method_description()}'로 변경되었습니다."
        )

    def print_week_details(self, week_number: int):
        """특정 주차의 상세 정보 출력"""
        if week_number not in self.weekly_pages:
            print(f"❌ {week_number}주차에 해당하는 페이지가 없습니다.")
            return

        pages = self.weekly_pages[week_number]

        # 주차 정보 헤더
        header_info = f"{week_number}주차 상세 정보 ({len(pages)}개 페이지)"
        if self.week_calculation_method == "project" and pages:
            week_summary = pages[0]["_date_info"].get("week_summary")
            if week_summary:
                header_info += f"\n📅 기간: {week_summary['korean_range']}"

        print(f"\n" + "=" * 60)
        print(f"📋 {header_info}")
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

    def summarize_week(
        self,
        week_number: int,
        summary_type: str = "weekly",
        format_instruction: str = "",
    ):
        """특정 주차의 모든 페이지를 요약"""
        if not self.summarizer:
            print("❌ AI 요약기가 설정되지 않았습니다.")
            return

        if week_number not in self.weekly_pages:
            print(f"❌ {week_number}주차에 해당하는 페이지가 없습니다.")
            return

        pages = self.weekly_pages[week_number]

        # 주차 정보 헤더
        header_info = f"{week_number}주차 AI 요약 ({len(pages)}개 페이지)"
        if self.week_calculation_method == "project" and pages:
            week_summary = pages[0]["_date_info"].get("week_summary")
            if week_summary:
                header_info += f"\n📅 기간: {week_summary['korean_range']}"

        print(f"\n" + "=" * 60)
        print(f"🤖 {header_info}")
        print("=" * 60)

        # 모든 페이지 내용을 하나의 텍스트로 합치기
        all_content = []

        for page in pages:
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

            # 페이지 헤더 추가
            all_content.append(f"\n=== {korean_date} - {title} ===")

            # 본문 내용 가져오기
            try:
                blocks_tree = self.client.get_block_tree(page["id"])
                if blocks_tree:
                    content = NotionBlockRenderer.render_blocks(blocks_tree)
                    if content.strip():
                        all_content.append(content)
                    else:
                        all_content.append("내용이 비어있습니다.")
                else:
                    all_content.append("내용이 비어있습니다.")
            except NotionAPIError as e:
                all_content.append(f"내용을 가져올 수 없습니다: {e}")

        # 전체 내용을 합쳐서 요약 실행
        combined_content = "\n".join(all_content)

        # 내용이 너무 적은 경우 체크
        if len(combined_content.strip()) < 10:
            print("❌ 요약할 내용이 충분하지 않습니다.")
            return ""

        try:
            # 요약 타입에 따라 다른 메서드 호출
            if summary_type == "weekly":
                summary = self.summarizer.weekly_summarize(
                    combined_content, format_instruction
                )
            elif summary_type == "problem":
                summary = self.summarizer.problem_summarize(
                    combined_content, format_instruction
                )
            elif summary_type == "thoughts":
                summary = self.summarizer.thoughts_summarize(
                    combined_content, format_instruction
                )
            elif summary_type == "plan":
                summary = self.summarizer.plan_summarize(
                    combined_content, format_instruction
                )
            else:
                summary = self.summarizer.summarize(
                    combined_content, format_instruction
                )

            print(f"\n📝 {summary_type.upper()} 요약 결과:")
            print("-" * 50)
            print(summary)

            return summary

        except Exception as e:
            print(f"❌ 요약 중 오류가 발생했습니다: {e}")
            return ""

    def generate_week_report(
        self,
        week_number: int,
        week_input: int,
        start_date: str = None,
        end_date: str = None,
        student: str = "황은비",
    ) -> Dict[str, str]:
        """특정 주차의 보고서 생성 (Word + PDF)"""
        if not self.summarizer:
            print("❌ AI 요약기가 설정되지 않았습니다.")
            return {}

        if week_number not in self.weekly_pages:
            print(f"❌ {week_number}주차에 해당하는 페이지가 없습니다.")
            return {}

        print(f"\n📋 {week_number}주차 보고서 생성 중...")

        # 4가지 요약 생성
        summaries = {}
        summary_types = ["weekly", "problem", "thoughts", "plan"]

        for summary_type in summary_types:
            print(f"🤖 {summary_type} 요약 생성 중...")
            summary = self.summarize_week(week_number, summary_type)
            summaries[summary_type] = summary

        # 날짜 정보 자동 생성
        if not start_date or not end_date:
            pages = self.weekly_pages[week_number]

            # 프로젝트 기준 주차인 경우 주차 요약에서 날짜 가져오기
            if self.week_calculation_method == "project" and pages:
                week_summary = pages[0]["_date_info"].get("week_summary")
                if week_summary:
                    start_date = start_date or week_summary["start_date"].strftime(
                        "%Y.%m.%d"
                    )
                    end_date = end_date or week_summary["end_date"].strftime("%Y.%m.%d")

            # 그 외의 경우 페이지 날짜에서 추출
            if not start_date or not end_date:
                dates = []
                for page in pages:
                    page_date = NotionPageFormatter.get_page_date(page["properties"])
                    if page_date:
                        dates.append(page_date)

                if dates:
                    dates.sort()
                    start_date = start_date or dates[0]
                    end_date = end_date or dates[-1]
                else:
                    from datetime import datetime, timedelta

                    today = datetime.now()
                    start_date = start_date or (today - timedelta(days=6)).strftime(
                        "%Y.%m.%d"
                    )
                    end_date = end_date or today.strftime("%Y.%m.%d")

        # 보고서 생성
        try:
            report_paths = self.report_generator.generate_reports(
                week_number=week_number,
                week_input=week_input,
                summaries=summaries,
                start_date=start_date,
                end_date=end_date,
                student=student,
            )

            print(f"✅ {week_number}주차 보고서 생성 완료!")
            return report_paths

        except Exception as e:
            print(f"❌ 보고서 생성 중 오류: {e}")
            return {}

    def get_available_weeks(self) -> List[int]:
        """사용 가능한 주차 목록 반환"""
        return sorted(self.weekly_pages.keys())

    def print_calculation_method_info(self):
        """현재 주차 계산 방식 정보 출력"""
        print(f"\n📅 현재 주차 계산 방식: {self._get_calculation_method_description()}")

        if self.week_calculation_method == "project":
            print(f"📍 프로젝트 시작일: {DateUtils.PROJECT_START_DATE}")
            current_week = DateUtils.get_current_project_week()
            print(f"🗓️  현재 프로젝트 주차: {current_week}주차")

            week_summary = DateUtils.get_week_summary(current_week)
            if week_summary["start_date"]:
                print(f"📅 현재 주차 범위: {week_summary['korean_range']}")
