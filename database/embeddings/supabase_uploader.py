import os
import pickle
import sqlite3
from typing import Any

from dotenv import load_dotenv
from supabase import create_client
from tqdm import tqdm


def get_total_rows(cursor: sqlite3.Cursor) -> int:
    """Get total number of rows in the database"""
    cursor.execute("SELECT COUNT(*) FROM product_info")
    return cursor.fetchone()[0]


def get_ordered_batch(cursor: sqlite3.Cursor, batch_size: int, offset: int) -> list[tuple]:
    """Get ordered batch of data from SQLite"""
    cursor.execute(
        """
        SELECT id, main, sub1, sub2, sub3, embedding
        FROM product_info
        ORDER BY main, sub1, sub2
        LIMIT ? OFFSET ?
        """,
        (batch_size, offset),
    )
    return cursor.fetchall()


def transform_batch_data(rows: list[tuple]) -> list[dict[str, Any]]:
    """Transform SQLite rows into Supabase compatible format"""
    return [
        {
            "id": str(row[0]),
            "main": row[1],
            "sub1": row[2],
            "sub2": row[3],
            "sub3": row[4],
            "embedding": pickle.loads(row[5]).tolist(),  # noqa: S301
        }
        for row in rows
    ]


def upload_batch_to_supabase(supabase, batch_data: list[dict[str, Any]]) -> int:
    """Upload a batch of data to Supabase"""
    if not batch_data:
        return 0

    try:
        # 기존 데이터 삭제 (ID가 중복되는 경우)
        ids = [row["id"] for row in batch_data]
        supabase.table("product_info").delete().in_("id", ids).execute()

        # 새 데이터 삽입
        result = supabase.table("product_info").insert(batch_data).execute()  # noqa: F841
        return len(batch_data)
    except Exception as e:
        print(f"\nError during upload: {e!s}")
        return 0


def upload_category_data(db_path: str, batch_size: int = 100):
    """카테고리 데이터를 Supabase에 업로드"""
    # 환경 설정
    ROOT_DIR = Path(__file__).parents[2]
    load_dotenv(ROOT_DIR / ".env")
    supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

    # DB 연결 및 초기화
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        total_rows = get_total_rows(cursor)
        successful = 0
        errors = 0

        # 데이터 처리 및 업로드
        with tqdm(total=total_rows, desc="Uploading") as pbar:
            for offset in range(0, total_rows, batch_size):
                try:
                    # 정렬된 배치 데이터 가져오기
                    rows = get_ordered_batch(cursor, batch_size, offset)

                    # 데이터 변환
                    batch_data = transform_batch_data(rows)

                    # 데이터 업로드
                    uploaded = upload_batch_to_supabase(supabase, batch_data)
                    successful += uploaded

                    if uploaded < len(batch_data):
                        errors += 1

                    pbar.update(len(batch_data))
                    pbar.set_postfix({"success": successful, "errors": errors})

                except Exception as e:
                    print(f"\nError at offset {offset}: {e!s}")
                    errors += 1
                    pbar.update(batch_size)

        return total_rows, successful, errors


if __name__ == "__main__":
    total, success, fails = upload_category_data("category_embeddings_MiniLM.db")
    print("\nUpload completed!")
    print(f"Total processed: {total}")
    print(f"Successfully uploaded: {success}")
    print(f"Failed: {fails}")
