import json
import os
from dataclasses import dataclass

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from supabase import Client, create_client

# Load environment variables at the start
load_dotenv()


class HierarchicalCategorySearch:
    def __init__(self, supabase_url: str, supabase_key: str):
        """
        Initialize the category search with Supabase connection

        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase project API key
        """
        # Initialize OpenAI client
        self.client = OpenAI(
            api_key=os.getenv("UPSTAGE_API_KEY"), base_url=os.getenv("UPSTAGE_API_BASE_URL", "https://api.upstage.ai/v1/solar")
        )

        # Initialize Supabase client
        self.supabase: Client = create_client(supabase_url, supabase_key)

        # Load data from Supabase
        self.refresh_data()

    def refresh_data(self):
        """Supabase에서 최신 카테고리 데이터를 가져옴"""
        response = self.supabase.table("product_info").select("id,main,sub1,sub2,sub3").execute()
        self.df = pd.DataFrame(response.data)

    def get_unique_values(self, level: str, parent_conditions: dict[str, str] | None = None) -> list[str]:
        """특정 레벨의 고유한 값들을 가져옴

        후보가 없는 경우, parent_conditions를 하나씩 제거하면서 가능한 가장 구체적인 후보를 찾음
        """
        df_filtered = self.df.copy()

        if parent_conditions:
            # 가장 구체적인 조건부터 시도
            conditions = list(parent_conditions.items())
            while conditions and df_filtered[df_filtered[level].notna()].empty:
                df_filtered = self.df.copy()
                # 마지막 조건을 제거하고 다시 시도
                conditions.pop()
                # 남은 조건들 적용
                for col, value in conditions:
                    df_filtered = df_filtered[df_filtered[col] == value]

        return df_filtered[level].dropna().unique().tolist()

    def find_best_category(self, input_text: str) -> dict[str, str]:
        """입력 텍스트에 대한 최적의 카테고리 조합을 찾음"""
        result = {}
        category_levels = ["main", "sub1", "sub2", "sub3"]

        for i, current_level in enumerate(category_levels):
            # 상위 카테고리들의 조건 생성
            parent_conditions = {level: result[level] for level in category_levels[:i] if level in result}

            # 현재 레벨의 카테고리 후보들 가져오기
            candidates = self.get_unique_values(current_level, parent_conditions)
            if not candidates:
                break

            # 컨텍스트 생성
            context = ", ".join(f"{k}: {v}" for k, v in parent_conditions.items()) if parent_conditions else ""

            # 최적의 카테고리 찾기
            best_category = self.find_best_match(input_text, candidates, context)
            if best_category:
                result[current_level] = best_category

        return result

    def find_best_match(self, query: str, candidates: list[str], context: str = "") -> str:
        """LLM을 사용하여 주어진 후보들 중에서 가장 적합한 카테고리를 찾음"""
        if not candidates:
            return None
        prompt = f"""You are a product categorization expert for an e-commerce platform.
        Your task is to classify the given product into the most appropriate category.

Product to categorize: "{query}"
{f"Current hierarchy: {context}" if context else ""}

Available categories:
{", ".join(candidates)}

Key instructions:
1. First identify the product's basic type (Is it food? electronics? clothing? etc.)
2. Consider the product's main purpose and features
3. Choose the MOST SPECIFIC category that correctly matches the product
4. Ensure logical consistency with any existing category path
5. When in doubt, prioritize obvious category matches over subtle distinctions

Return ONLY the exact category name from the available options. No explanation or additional text.
"""

        messages = [{"role": "user", "content": prompt}]
        response = self.client.chat.completions.create(model="solar-pro", messages=messages)
        selected = response.choices[0].message.content.strip()

        # 반환된 카테고리가 후보 목록에 없는 경우 첫 번째 후보 반환
        if selected not in candidates:
            return candidates[0]

        return selected


@dataclass
class CategoryResponse:
    input_text: str
    categories: dict[str, str]

    def to_dict(self) -> dict:
        return {"input_text": self.input_text, "categories": self.categories}


def main():
    # Supabase 연결 정보
    url: str = os.getenv("SUPABASE_URL")
    key: str = os.getenv("SUPABASE_KEY")

    # 테스트 실행
    searcher = HierarchicalCategorySearch(url, key)

    # 테스트할 입력값들
    test_inputs = ["gaming laptop with RTX 4090", "wireless noise cancelling headphones", "organic fresh bananas"]

    results = []
    for input_text in test_inputs:
        categories = searcher.find_best_category(input_text)
        response = CategoryResponse(input_text=input_text, categories=categories)
        results.append(response.to_dict())

    # JSON 형식으로 출력
    print(json.dumps({"results": results}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
