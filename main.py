from src.config import APIConfig
from src.client import NotionClient
from src.exceptions import NotionAPIError
from src.renderers import NotionBlockRenderer, NotionPageFormatter
from src.weekly_manager import WeeklyManager
from typing import Dict, Any
from src.ai_summarizer import ReportSummarizer
import os


def print_database_summary(db_info: Dict[str, Any]) -> None:
    """데이터베이스 요약 정보 출력"""
    title = "제목 없음"
    if db_info.get("title"):
        title = db_info["title"][0]["plain_text"]

    print("=" * 60)
    print("📊 NOTION 데이터베이스 정보")
    print("=" * 60)
    print(f"제목: {title}")
    print(f"생성일: {db_info['created_time']}")
    print(f"ID: {db_info['id']}")
    print(f"URL: {db_info['url']}")

    # 속성 정보
    properties = db_info.get("properties", {})
    if properties:
        print(f"\n속성 목록 ({len(properties)}개):")
        for prop_name, prop_info in properties.items():
            prop_type = prop_info.get("type", "unknown")
            print(f"  • {prop_name} ({prop_type})")


def interactive_week_selection(weekly_manager: WeeklyManager):
    """대화형 주차 선택"""
    available_weeks = weekly_manager.get_available_weeks()

    if not available_weeks:
        print("📭 선택할 수 있는 주차가 없습니다.")
        return

    print(f"\n💡 사용 가능한 주차: {', '.join(map(str, available_weeks))}주차")

    while True:
        try:
            user_input = input(f"\n보고 싶은 주차를 입력하세요 (종료: q): ").strip()

            if user_input.lower() == "q":
                print("👋 프로그램을 종료합니다.")
                break

            week_num = int(user_input)

            if week_num in available_weeks:
                # 상세 보기와 요약 선택 메뉴 추가
                print(f"\n📋 {week_num}주차 옵션:")
                print("1. 상세 내용 보기")
                print("2. AI 요약 보기")

                choice = input("선택하세요 (1-2): ").strip()

                if choice == "1":
                    weekly_manager.print_week_details(week_num)
                elif choice == "2":
                    # 4가지 요약 타입 모두 실행
                    if weekly_manager.summarizer:
                        print(f"\n🤖 {week_num}주차 전체 AI 요약 생성 중...")

                        summary_types = [
                            ("weekly", "주간 요약"),
                            ("problem", "문제점 분석"),
                            ("thoughts", "생각 정리"),
                            ("plan", "계획 요약"),
                        ]

                        for summary_type, summary_name in summary_types:
                            print(f"\n{'='*80}")
                            print(f"📝 {summary_name.upper()} ({summary_type})")
                            print(f"{'='*80}")
                            weekly_manager.summarize_week(week_num, summary_type)
                            print("\n" + "-" * 80)
                    else:
                        print("❌ AI 요약기가 설정되지 않았습니다.")
                else:
                    print("❌ 잘못된 선택입니다.")
            else:
                print(
                    f"❌ {week_num}주차는 존재하지 않습니다. 사용 가능한 주차: {', '.join(map(str, available_weeks))}주차"
                )

        except ValueError:
            print("❌ 숫자를 입력해주세요.")
        except KeyboardInterrupt:
            print("\n\n👋 프로그램을 종료합니다.")
            break


def main():
    """메인 함수"""
    try:
        print("🚀 Notion API 클라이언트 시작")

        # 설정 로드
        config = APIConfig.from_env()
        client = NotionClient(config)

        # AI 요약기 설정 (OpenAI API 키가 있는 경우에만)
        summarizer = None
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key:
            try:
                summarizer = ReportSummarizer(openai_api_key)
                print("✅ AI 요약기가 설정되었습니다.")
            except Exception as e:
                print(f"⚠️  AI 요약기 설정 실패: {e}")
        else:
            print(
                "⚠️  OPENAI_API_KEY가 설정되지 않았습니다. AI 요약 기능을 사용할 수 없습니다."
            )

        # 데이터베이스 정보 조회
        print("\n📥 데이터베이스 정보를 가져오는 중...")
        db_info = client.get_database()
        print_database_summary(db_info)

        # 모든 페이지 조회
        print("\n📋 데이터베이스 페이지 쿼리 중...")
        pages = client.query_database_all()
        print(f"✅ 총 {len(pages)}개의 페이지를 찾았습니다.")

        if not pages:
            print("📭 페이지가 없습니다.")
            return

        # 주차별 분석 (AI 요약기와 함께)
        print("\n🗓️  페이지를 주차별로 분석 중...")
        weekly_manager = WeeklyManager(client, summarizer)
        weekly_pages = weekly_manager.analyze_pages_by_week(pages)

        # 주차별 요약 출력
        weekly_manager.print_weekly_summary()

        # 대화형 주차 선택
        interactive_week_selection(weekly_manager)

    except NotionAPIError as e:
        print(f"❌ Notion API 에러: {e}")
    except ValueError as e:
        print(f"❌ 설정 에러: {e}")
    except Exception as e:
        print(f"❌ 예상치 못한 에러: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
