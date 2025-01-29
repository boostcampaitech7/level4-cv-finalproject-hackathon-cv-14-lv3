import os
import sqlite3
from base64 import b64decode, b64encode

import numpy as np
import pandas as pd
from openai import OpenAI
from tqdm import tqdm


class CategoryEmbeddingSystem:
    def __init__(self, db_path: str = "category_embeddings.db", api_key: str | None = None):
        if not api_key:
            raise ValueError("Upstage API key is required")

        self.client = OpenAI(api_key=api_key, base_url="https://api.upstage.ai/v1/solar")
        self.db_path = db_path
        self.setup_database()

    def setup_database(self) -> None:
        """Initialize SQLite database with hierarchical structure"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

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

        c.execute("CREATE INDEX IF NOT EXISTS idx_main ON category_hierarchy(main)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_sub1 ON category_hierarchy(sub1)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_sub2 ON category_hierarchy(sub2)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_sub3 ON category_hierarchy(sub3)")

        conn.commit()
        conn.close()

    def serialize_embedding(self, embedding: np.ndarray) -> bytes:
        """Convert numpy array to bytes using base64 encoding"""
        return b64encode(embedding.tobytes())

    def deserialize_embedding(self, data: bytes) -> np.ndarray:
        """Convert base64 encoded bytes back to numpy array"""
        return np.frombuffer(b64decode(data))

    def get_embedding(self, text: str) -> np.ndarray:
        """Get embedding from Upstage API"""
        response = self.client.embeddings.create(input=text, model="embedding-query")
        return np.array(response.data[0].embedding)

    def process_categories(self, csv_path: str) -> None:
        """Process CSV file and store embeddings with hierarchy"""
        print(f"Reading CSV file: {csv_path}")
        df = pd.read_csv(csv_path)

        unique_categories = set()

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

        conn = sqlite3.connect(self.db_path)

        for main, sub1, sub2, sub3 in tqdm(categories, desc="Processing categories"):
            parts = [p for p in [main, sub1, sub2, sub3] if p]
            text = " > ".join(parts)

            try:
                embedding = self.get_embedding(text)
                embedding_bytes = self.serialize_embedding(embedding)

                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO category_hierarchy
                    (main, sub1, sub2, sub3, embedding)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (main, sub1, sub2, sub3, embedding_bytes),
                )
                conn.commit()
            except Exception as e:
                print(f"Error processing category '{text}': {e!s}")

        conn.close()
        print("Database build completed!")

    def test_embeddings(self, test_queries: list[str] | None = None) -> None:
        """Test embeddings with sample queries"""
        if test_queries is None:
            test_queries = ["laptop computer", "organic food", "children's toys"]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for query in test_queries:
            print(f"\nTesting query: {query}")
            try:
                query_embedding = self.get_embedding(query)
                cursor.execute("SELECT main, sub1, sub2, sub3, embedding FROM category_hierarchy")

                similarities = []
                for row in cursor.fetchall():
                    main, sub1, sub2, sub3, emb_bytes = row
                    category_embedding = self.deserialize_embedding(emb_bytes)

                    similarity = np.dot(query_embedding, category_embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(category_embedding)
                    )

                    path = " > ".join(filter(None, [main, sub1, sub2, sub3]))
                    similarities.append((path, similarity))

                top_5 = sorted(similarities, key=lambda x: x[1], reverse=True)[:5]
                print("\nTop 5 matching categories:")
                for path, score in top_5:
                    print(f"{path}: {score:.4f}")

            except Exception as e:
                print(f"Error testing query '{query}': {e!s}")

        conn.close()


def main() -> None:
    api_key = os.getenv("UPSTAGE_API_KEY")
    if not api_key:
        print("Please enter your Upstage API key:")
        api_key = input().strip()

    csv_path = "product_info.csv"
    db_path = "category_embeddings.db"

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    print("Starting category embeddings database build with Upstage API...")
    system = CategoryEmbeddingSystem(db_path=db_path, api_key=api_key)
    system.process_categories(csv_path)

    print("\nTesting embeddings...")
    system.test_embeddings()


if __name__ == "__main__":
    main()
