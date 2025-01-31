import ast
import os
import sqlite3

from supabase import Client, create_client

# Supabase 연결 정보
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")


# Supabase 클라이언트 생성
supabase: Client = create_client(url, key)

# SQLite DB 연결
conn = sqlite3.connect("category_embeddings_MiniLM.db")
cursor = conn.cursor()

# 전체 데이터 수 확인
cursor.execute("SELECT COUNT(*) FROM product_info")
total_rows = cursor.fetchone()[0]
print(f"Total rows to process: {total_rows}")


def process_embedding(embedding_bytes):
    """
    직렬화된 embedding 데이터를 float32 배열로 변환
    """
    try:
        numpy_array = ast.literal_eval(embedding_bytes)

        return numpy_array.tolist()
    except Exception as e:
        print(f"Error processing embedding: {e}")
        return None


# 첫 번째 row 테스트
cursor.execute("SELECT * FROM product_info LIMIT 1")
test_row = cursor.fetchone()
print("\nTesting first row:")
print("ID:", test_row[0])
print("Main category:", test_row[1])
processed_test = process_embedding(test_row[5])
print("Embedding dimension:", len(processed_test) if processed_test else None)

# 데이터 처리 및 업로드
batch_size = 100
successful_uploads = 0
errors = 0

for offset in range(0, total_rows, batch_size):
    try:
        cursor.execute(
            """
            SELECT id, main, sub1, sub2, sub3, embedding
            FROM product_info
            LIMIT ? OFFSET ?
        """,
            (batch_size, offset),
        )

        batch_rows = cursor.fetchall()
        data_batch = []

        for row in batch_rows:
            processed_embedding = process_embedding(row[5])
            if processed_embedding is not None:
                data = {
                    "id": str(row[0]),
                    "main": row[1],
                    "sub1": row[2] if row[2] is not None else "",
                    "sub2": row[3] if row[3] is not None else "",
                    "sub3": row[4] if row[4] is not None else "",
                    "embedding": processed_embedding,
                }
                data_batch.append(data)

        if data_batch:
            try:
                result = supabase.table("product_info").insert(data_batch).execute()
                successful_uploads += len(data_batch)
            except Exception as e:
                print(f"\nUpload error for batch at offset {offset}:")
                print(f"Error message: {e!s}")
                errors += 1

        print(f"Processed {min(offset + batch_size, total_rows)}/{total_rows} rows...")
        print(f"Successfully uploaded: {successful_uploads}")
        print(f"Errors: {errors}")

    except Exception as e:
        errors += 1
        print(f"Processing error at batch starting at row {offset}: {e!s}")

conn.close()

print("\nUpload completed!")
print(f"Total processed: {total_rows}")
print(f"Successfully uploaded: {successful_uploads}")
print(f"Failed: {errors}")
