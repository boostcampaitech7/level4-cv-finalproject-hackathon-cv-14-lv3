import os
import sqlite3
from base64 import b64decode, b64encode
from typing import ClassVar

import numpy as np
from openai import OpenAI


class HierarchicalCategorySearch:
    VALID_LEVELS: ClassVar[set[str]] = {"main", "sub1", "sub2", "sub3"}

    def __init__(self, db_path: str = "category_embeddings.db", api_key: str | None = None):
        if not api_key:
            api_key = os.getenv("UPSTAGE_API_KEY")
            if not api_key:
                raise ValueError("Upstage API key is required")

        self.client = OpenAI(api_key=api_key, base_url="https://api.upstage.ai/v1/solar")
        self.db_path = db_path

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

    def get_unique_values(self, level: str, parent_conditions: dict[str, str] | None = None) -> list[str]:
        """Get unique values for a specific category level"""
        if level not in self.VALID_LEVELS:
            raise ValueError(f"Invalid level: {level}")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        params: list[str] = []
        query_parts = ["SELECT DISTINCT ? FROM category_hierarchy WHERE ? != ''"]
        params.extend([level, level])

        if parent_conditions:
            conditions = []
            for k, v in parent_conditions.items():
                if k not in self.VALID_LEVELS:
                    raise ValueError(f"Invalid condition key: {k}")
                conditions.append("? = ?")
                params.extend([k, v])

            if conditions:
                query_parts.append("AND")
                query_parts.append(" AND ".join(conditions))

        query = " ".join(query_parts)
        cursor.execute(query, params)

        values = [row[0] for row in cursor.fetchall()]
        conn.close()
        return values

    def get_embedding_for_category(self, category_values: dict[str, str]) -> np.ndarray | None:
        """Get embedding for a specific category combination"""
        if not all(k in self.VALID_LEVELS for k in category_values.keys()):
            raise ValueError("Invalid category keys")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 안전한 쿼리 구성
        placeholders = []
        params = []

        # VALID_LEVELS에 있는 필드만 사용
        for field in self.VALID_LEVELS:
            if field in category_values:
                placeholders.append(f"{field} = ?")
                params.append(category_values[field])

        # 미리 정의된 고정 쿼리 사용
        base_query = "SELECT embedding FROM category_hierarchy"
        if placeholders:
            query = f"{base_query} WHERE {' AND '.join(placeholders)}"
        else:
            query = base_query

        try:
            cursor.execute(query, params)
            result = cursor.fetchone()

            if result:
                return self.deserialize_embedding(result[0])
            return None

        finally:
            conn.close()

    def find_best_match(
        self, query_embedding: np.ndarray, candidates: list[str], parent_values: dict[str, str]
    ) -> tuple[str | None, float]:
        """Find the best matching category from candidates"""
        best_similarity = -1
        best_candidate = None

        for candidate in candidates:
            current_values = parent_values.copy()
            current_level = f"sub{len(parent_values)}" if parent_values else "main"
            current_values[current_level] = candidate

            category_embedding = self.get_embedding_for_category(current_values)
            if category_embedding is None:
                continue

            similarity = np.dot(query_embedding, category_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(category_embedding)
            )

            if similarity > best_similarity:
                best_similarity = similarity
                best_candidate = candidate

        return best_candidate, best_similarity

    def find_best_category(self, input_text: str) -> dict[str, str]:
        """Find the best category combination for input text"""
        query_embedding = self.get_embedding(input_text)
        result = {}

        # 1. Find Main category
        main_categories = self.get_unique_values("main")
        best_main, main_similarity = self.find_best_match(query_embedding, main_categories, {})

        if best_main is None:
            return result

        result["main"] = best_main
        print(f"\n1. Selected Main Category: {best_main}")

        # 2. Find Sub1 category
        sub1_categories = self.get_unique_values("sub1", {"main": best_main})
        if sub1_categories:
            best_sub1, sub1_similarity = self.find_best_match(query_embedding, sub1_categories, {"main": best_main})
            if best_sub1:
                result["sub1"] = best_sub1
                print(f"2. Selected Sub1 Category: {best_sub1}")

                # 3. Find Sub2 category
                sub2_categories = self.get_unique_values("sub2", {"main": best_main, "sub1": best_sub1})
                if sub2_categories:
                    best_sub2, sub2_similarity = self.find_best_match(
                        query_embedding, sub2_categories, {"main": best_main, "sub1": best_sub1}
                    )
                    if best_sub2:
                        result["sub2"] = best_sub2
                        print(f"3. Selected Sub2 Category: {best_sub2}")

                        # 4. Find Sub3 category
                        sub3_categories = self.get_unique_values("sub3", {"main": best_main, "sub1": best_sub1, "sub2": best_sub2})
                        if sub3_categories:
                            best_sub3, sub3_similarity = self.find_best_match(
                                query_embedding, sub3_categories, {"main": best_main, "sub1": best_sub1, "sub2": best_sub2}
                            )
                            if best_sub3:
                                result["sub3"] = best_sub3
                                print(f"4. Selected Sub3 Category: {best_sub3}")

        return result


def main() -> None:
    api_key = os.getenv("UPSTAGE_API_KEY")
    if not api_key:
        print("Please enter your Upstage API key:")
        api_key = input().strip()

    searcher = HierarchicalCategorySearch(api_key=api_key)

    test_inputs = [
        "gaming laptop",
        "organic banana",
        "wireless headphones",
    ]

    for input_text in test_inputs:
        print(f"\n=== Finding categories for: {input_text} ===")
        result = searcher.find_best_category(input_text)

        print("\nFinal Result:")
        print(f"Input: {input_text}")
        print("Categories:")
        for level, category in result.items():
            print(f"- {level}: {category}")
        print("-" * 50)


if __name__ == "__main__":
    main()
