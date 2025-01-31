import os

import numpy as np
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from supabase import Client, create_client


class HierarchicalCategorySearch:
    def __init__(self, supabase_url: str, supabase_key: str):
        self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        self.supabase: Client = create_client(supabase_url, supabase_key)

    def get_unique_values(self, level: str, parent_conditions: dict[str, str] | None = None) -> list[str]:
        """특정 레벨의 고유한 값들을 가져옴"""
        query = self.supabase.table("product_info").select(f"{level}::text").neq(level, "")

        if parent_conditions:
            for key, value in parent_conditions.items():
                query = query.eq(key, value)

        result = query.execute()

        # 결과에서 중복을 제거합니다
        unique_values = list(set(row[level] for row in result.data if row[level]))
        return sorted(unique_values)  # 정렬된 결과 반환

    def get_embedding_for_category(self, category_values: dict[str, str]) -> np.ndarray | None:
        """특정 카테고리 조합의 임베딩을 가져옴"""
        query = self.supabase.table("product_info").select("embedding")

        for key, value in category_values.items():
            query = query.eq(key, value)

        result = query.execute()

        if result.data:
            # Supabase에서는 이미 리스트 형태로 저장되어 있으므로 바로 numpy array로 변환
            embedding = np.array(result.data[0]["embedding"])
            return embedding
        return None

    def find_best_category(self, input_text: str) -> dict[str, str]:
        """입력 텍스트에 대한 최적의 카테고리 조합을 찾음"""
        query_embedding = self.model.encode([input_text])[0]
        result = {}

        # 1. Main 카테고리 찾기
        main_categories = self.get_unique_values("main")
        best_main = self.find_best_match(query_embedding, main_categories, {})
        result["main"] = best_main
        print(f"\n1. Selected Main Category: {best_main}")

        # 2. Sub1 카테고리 찾기
        sub1_categories = self.get_unique_values("sub1", {"main": best_main})
        if sub1_categories:
            best_sub1 = self.find_best_match(query_embedding, sub1_categories, {"main": best_main})
            result["sub1"] = best_sub1
            print(f"2. Selected Sub1 Category: {best_sub1}")

            # 3. Sub2 카테고리 찾기
            sub2_categories = self.get_unique_values("sub2", {"main": best_main, "sub1": best_sub1})
            if sub2_categories:
                best_sub2 = self.find_best_match(query_embedding, sub2_categories, {"main": best_main, "sub1": best_sub1})
                result["sub2"] = best_sub2
                print(f"3. Selected Sub2 Category: {best_sub2}")

                # 4. Sub3 카테고리 찾기
                sub3_categories = self.get_unique_values("sub3", {"main": best_main, "sub1": best_sub1, "sub2": best_sub2})
                if sub3_categories:
                    best_sub3 = self.find_best_match(
                        query_embedding, sub3_categories, {"main": best_main, "sub1": best_sub1, "sub2": best_sub2}
                    )
                    result["sub3"] = best_sub3
                    print(f"4. Selected Sub3 Category: {best_sub3}")

        return result

    def find_best_match(self, query_embedding: np.ndarray, candidates: list[str], parent_values: dict[str, str]) -> str:
        """주어진 후보들 중에서 가장 유사한 카테고리를 찾음"""
        best_similarity = -1
        best_candidate = None

        for candidate in candidates:
            # 현재 레벨의 카테고리 값을 포함한 전체 경로 생성
            current_values = parent_values.copy()
            current_level = "sub" + str(len(parent_values)) if parent_values else "main"
            current_values[current_level] = candidate

            # 해당 카테고리 조합의 임베딩 가져오기
            category_embedding = self.get_embedding_for_category(current_values)
            if category_embedding is None:
                continue

            # 코사인 유사도 계산
            similarity = np.dot(query_embedding, category_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(category_embedding)
            )

            print(f"  - {candidate}: {similarity:.4f}")

            if similarity > best_similarity:
                best_similarity = similarity
                best_candidate = candidate

        return best_candidate


def main():
    # Supabase 연결 정보
    load_dotenv()
    url: str = os.getenv("SUPABASE_URL")
    key: str = os.getenv("SUPABASE_KEY")

    # 테스트 실행
    searcher = HierarchicalCategorySearch(url, key)

    # 테스트할 입력값들
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
