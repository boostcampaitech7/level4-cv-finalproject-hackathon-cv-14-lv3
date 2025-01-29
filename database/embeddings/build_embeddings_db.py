import os
import pickle
import sqlite3

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer


class CategoryEmbeddingSystem:
    def __init__(self, db_path: str = "category_embeddings.db"):
        self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        self.db_path = db_path
        self.setup_database()

    def setup_database(self):
        """Initialize SQLite database with hierarchical structure"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # 계층 구조를 저장하는 테이블
        c.execute("""
        CREATE TABLE IF NOT EXISTS category_hierarchy
        (id INTEGER PRIMARY KEY,
         main TEXT,
         sub1 TEXT,
         sub2 TEXT,
         sub3 TEXT,
         embedding BLOB,
         UNIQUE(main, sub1, sub2, sub3))
        """)

        # 각 레벨별 인덱스 생성
        c.execute("CREATE INDEX IF NOT EXISTS idx_main ON category_hierarchy(main)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_sub1 ON category_hierarchy(sub1)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_sub2 ON category_hierarchy(sub2)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_sub3 ON category_hierarchy(sub3)")

        conn.commit()
        conn.close()

    def process_categories(self, csv_path: str):
        """Process CSV file and store embeddings with hierarchy"""
        print(f"Reading CSV file: {csv_path}")
        df = pd.read_csv(csv_path)

        # 중복 제거를 위한 집합
        unique_categories = set()

        # 각 계층별 카테고리 조합 수집
        for _, row in df.iterrows():
            main = str(row["Main"]).strip()
            sub1 = str(row["Sub1"]).strip()
            sub2 = str(row["Sub2"]).strip()
            sub3 = str(row["Sub3"]).strip()

            if main.lower() != "nan":
                unique_categories.add((main, "", "", ""))
                if sub1.lower() != "nan":
                    unique_categories.add((main, sub1, "", ""))
                    if sub2.lower() != "nan":
                        unique_categories.add((main, sub1, sub2, ""))
                        if sub3.lower() != "nan":
                            unique_categories.add((main, sub1, sub2, sub3))

        categories = list(unique_categories)
        print(f"Found {len(categories)} unique category combinations")

        # 배치 처리로 임베딩 계산 및 저장
        batch_size = 32
        conn = sqlite3.connect(self.db_path)

        for i in range(0, len(categories), batch_size):
            batch = categories[i : i + batch_size]

            # 각 카테고리 조합에 대한 텍스트 생성
            texts = []
            for main, sub1, sub2, sub3 in batch:
                text = main
                if sub1:
                    text += f" > {sub1}"
                if sub2:
                    text += f" > {sub2}"
                if sub3:
                    text += f" > {sub3}"
                texts.append(text)

            # 임베딩 계산
            embeddings = self.model.encode(texts)

            # 데이터베이스에 저장
            cursor = conn.cursor()
            for (main, sub1, sub2, sub3), embedding in zip(batch, embeddings, strict=False):
                embedding_blob = pickle.dumps(embedding)
                cursor.execute(
                    """
                INSERT OR REPLACE INTO category_hierarchy
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
        cursor.execute("SELECT main, sub1, sub2, sub3, embedding FROM category_hierarchy")

        similarities = []
        for main, sub1, sub2, sub3, embedding_blob in cursor.fetchall():
            embedding = pickle.loads(embedding_blob)
            similarity = np.dot(query_embedding, embedding) / (np.linalg.norm(query_embedding) * np.linalg.norm(embedding))

            # 계층 구조를 유지하면서 카테고리 경로 생성
            category_path = main
            if sub1:
                category_path += f" > {sub1}"
            if sub2:
                category_path += f" > {sub2}"
            if sub3:
                category_path += f" > {sub3}"

            similarities.append(
                {
                    "main": main,
                    "sub1": sub1 if sub1 else None,
                    "sub2": sub2 if sub2 else None,
                    "sub3": sub3 if sub3 else None,
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
    db_path = "category_embeddings.db"

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
