import os
import pickle
import sqlite3

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer


class CategoryEmbeddingSystem:
    def __init__(self, db_path: str = "category_embeddings_MiniLM.db"):
        self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        self.db_path = db_path
        self.setup_database()

    def setup_database(self):
        """Initialize SQLite database with hierarchical structure"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # 계층 구조를 저장하는 테이블
        c.execute("""
        CREATE TABLE IF NOT EXISTS product_info
        (id INTEGER PRIMARY KEY,
         main TEXT NOT NULL,
         sub1 TEXT NOT NULL,
         sub2 TEXT NOT NULL,
         sub3 TEXT NOT NULL,
         embedding BLOB NOT NULL,
         UNIQUE(main, sub1, sub2, sub3))
        """)

        # 각 레벨별 인덱스 생성
        c.execute("CREATE INDEX IF NOT EXISTS idx_main ON product_info(main)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_sub1 ON product_info(sub1)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_sub2 ON product_info(sub2)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_sub3 ON product_info(sub3)")

        conn.commit()
        conn.close()

    def _clean_category(self, value: str) -> str | None:
        """Clean category value and return None if invalid"""
        if pd.isna(value) or value.strip().lower() == "nan":
            return None
        cleaned = value.strip()
        return cleaned if cleaned else None

    def _get_valid_category_tuple(self, row: pd.Series) -> tuple[str, str | None, str | None, str | None] | None:
        """Convert row to clean category tuple, return None if invalid"""
        main = self._clean_category(str(row["Main"]))
        if not main:
            return None

        sub1 = self._clean_category(str(row["Sub1"]))
        sub2 = self._clean_category(str(row["Sub2"]))
        sub3 = self._clean_category(str(row["Sub3"]))

        # Ensure hierarchy is valid (no gaps)
        if sub2 and not sub1:
            return None
        if sub3 and not (sub1 and sub2):
            return None

        return (main, sub1, sub2, sub3)

    def _collect_valid_hierarchies(
        self, category_tuple: tuple[str, str | None, str | None, str | None]
    ) -> set[tuple[str, str | None, str | None, str | None]]:
        """Collect all valid hierarchical combinations from a category tuple"""
        main, sub1, sub2, sub3 = category_tuple
        hierarchies = {(main, None, None, None)}

        if sub1:
            hierarchies.add((main, sub1, None, None))
            if sub2:
                hierarchies.add((main, sub1, sub2, None))
                if sub3:
                    hierarchies.add((main, sub1, sub2, sub3))

        return hierarchies

    def process_categories(self, csv_path: str):
        """Process CSV file and store embeddings with hierarchy"""
        print(f"Reading CSV file: {csv_path}")
        df = pd.read_csv(csv_path)

        # 데이터프레임에서 직접 정렬된 카테고리 추출
        df_sorted = df.sort_values(["Main", "Sub1", "Sub2"])

        # 정렬된 순서로 카테고리 조합 수집
        categories = []
        seen = set()  # 중복 체크용

        for _, row in df_sorted.iterrows():
            main = str(row["Main"]).strip()
            sub1 = str(row["Sub1"]).strip()
            sub2 = str(row["Sub2"]).strip()
            sub3 = str(row["Sub3"]).strip()

            category_tuple = (main, sub1, sub2, sub3)
            if category_tuple not in seen:
                categories.append(category_tuple)
                seen.add(category_tuple)
        print(f"Found {len(categories)} valid unique category combinations")

        # 배치 처리로 임베딩 계산 및 저장
        batch_size = 32
        conn = sqlite3.connect(self.db_path)

        for i in range(0, len(categories), batch_size):
            batch = categories[i : i + batch_size]

            # 각 카테고리 조합에 대한 텍스트 생성
            texts = []
            for main, sub1, sub2, sub3 in batch:
                texts.append(f"{main} > {sub1} > {sub2} > {sub3}")

            # 임베딩 계산
            embeddings = self.model.encode(texts)

            # 데이터베이스에 저장
            cursor = conn.cursor()
            for (main, sub1, sub2, sub3), embedding in zip(batch, embeddings, strict=False):
                embedding_blob = pickle.dumps(embedding)
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO product_info
                    (main, sub1, sub2, sub3, embedding)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (main, sub1, sub2, sub3, embedding_blob),
                )

            conn.commit()
            print(f"Processed {min(i + batch_size, len(categories))}/{len(categories)} categories")

        conn.close()
        print("Database build completed!")

    def find_similar_categories(self, query: str, top_k: int = 5):
        """Find similar categories for a query"""
        # 쿼리 임베딩 계산
        query_embedding = self.model.encode([query])[0]

        # 데이터베이스에서 모든 카테고리와 임베딩 검색
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT main, sub1, sub2, sub3, embedding FROM product_info")

        similarities = []
        for main, sub1, sub2, sub3, embedding_blob in cursor.fetchall():
            embedding = pickle.loads(embedding_blob)  # noqa: S301
            similarity = np.dot(query_embedding, embedding) / (np.linalg.norm(query_embedding) * np.linalg.norm(embedding))

            # 계층 구조를 유지하면서 카테고리 경로 생성
            category_parts = [main]
            if sub1:
                category_parts.append(sub1)
            if sub2:
                category_parts.append(sub2)
            if sub3:
                category_parts.append(sub3)

            category_path = " > ".join(category_parts)

            similarities.append(
                {
                    "main": main,
                    "sub1": sub1,
                    "sub2": sub2,
                    "sub3": sub3,
                    "path": category_path,
                    "similarity": float(similarity),
                }
            )

        conn.close()

        # 유사도 기준으로 정렬하고 상위 k개 반환
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        return similarities[:top_k]


def main():
    # 현재 디렉토리에서 파일 찾기
    csv_path = "product_info.csv"
    db_path = "category_embeddings_MiniLM.db"

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    print("Starting category embeddings database build...")
    system = CategoryEmbeddingSystem(db_path=db_path)
    system.process_categories(csv_path)

    # 간단한 테스트 실행
    test_query = "potato chips"
    results = system.find_similar_categories(test_query)
    print("\nTest query:", test_query)
    for result in results:
        print(f"Category: {result['path']}")
        print(f"Similarity: {result['similarity']:.4f}")
        print()


if __name__ == "__main__":
    main()
