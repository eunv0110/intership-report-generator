from src.config import NotionConfig
from src.client import NotionClient
from src.exceptions import NotionAPIError
from src.renderers import NotionBlockRenderer, NotionPageFormatter
from typing import Dict, Any


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


def main():
    """메인 함수"""
    try:
        print("🚀 Notion API 클라이언트 시작")

        # 설정 로드
        config = NotionConfig.from_env()
        client = NotionClient(config)

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

        # 각 페이지 처리
        for i, page in enumerate(pages, 1):
            NotionPageFormatter.print_page_info(page, i)

            # 페이지 내용 조회 및 출력
            print("\n📄 본문 내용:")
            print("-" * 50)
            try:
                blocks_tree = client.get_block_tree(page["id"])
                if blocks_tree:
                    NotionBlockRenderer.render_blocks(blocks_tree)
                else:
                    print("📄 내용이 비어있습니다.")
            except NotionAPIError as e:
                print(f"❌ 내용을 가져올 수 없습니다: {e}")

            # 페이지 간 구분
            if i < len(pages):
                print("\n" + "=" * 80 + "\n")

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
