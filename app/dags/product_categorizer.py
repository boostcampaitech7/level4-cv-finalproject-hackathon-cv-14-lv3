import logging
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client

# httpx 로깅 레벨 설정
logging.getLogger("httpx").setLevel(logging.WARNING)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CategoryResult:
    text: str
    main: str
    sub1: str | None = None
    sub2: str | None = None
    sub3: str | None = None
    confidence: float = 0.0
    success: bool = False
    ensemble_info: dict | None = None

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "main": self.main,
            "sub1": self.sub1,
            "sub2": self.sub2,
            "sub3": self.sub3,
            "confidence": self.confidence,
            "success": self.success,
            "ensemble_info": self.ensemble_info,
        }


class CategorySearch:
    def __init__(self):
        env_path = Path(__file__).parents[2] / ".env"
        load_dotenv(env_path)
        self.client = OpenAI(
            api_key=os.getenv("UPSTAGE_API_KEY"), base_url=os.getenv("UPSTAGE_API_BASE_URL", "https://api.upstage.ai/v1/solar")
        )
        self.supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        self.categories: dict[str, set[str]] = defaultdict(set)
        self.category_hierarchy: dict[str, dict] = defaultdict(dict)
        self.trend_products: list[dict] = []
        self.example_cases: dict[str, list[dict]] = {}

        # 정규표현식 패턴 미리 컴파일
        self._compile_regex_patterns()

    def _compile_regex_patterns(self):
        """정규표현식 패턴 컴파일"""
        self._regex_patterns = {
            "category": re.compile(r"Category: (.+)"),
            "confidence": re.compile(r"Confidence: (0\.\d+|1\.0)"),
            "reasoning": re.compile(r"Reasoning: (.+)"),
        }

    def load_data(self):
        """Supabase에서 계층적 카테고리 데이터 로드 및 초기화"""
        logger.info("Loading hierarchical category data from Supabase...")

        try:
            # product_info 테이블에서 카테고리 데이터 로드
            category_response = self.supabase.table("product_info").select("main, sub1, sub2, sub3").execute()
            category_df = pd.DataFrame(category_response.data)

            # 데이터 상태 확인
            logger.info(f"Loaded category data shape: {category_df.shape}")

            # 계층적 구조로 카테고리 저장
            self.category_hierarchy = {}

            # 메인 카테고리 처리
            unique_mains = category_df["main"].dropna().unique()
            self.categories["main"] = set(unique_mains)

            for main_cat in unique_mains:
                self.category_hierarchy[main_cat] = {"sub1": {}}

                # main에 속하는 sub1 카테고리들 찾기
                sub1_mask = category_df["main"] == main_cat
                sub1_categories = category_df[sub1_mask]["sub1"].dropna().unique()

                for sub1_cat in sub1_categories:
                    self.category_hierarchy[main_cat]["sub1"][sub1_cat] = {"sub2": {}}

                    # sub1에 속하는 sub2 카테고리들 찾기
                    sub2_mask = (category_df["main"] == main_cat) & (category_df["sub1"] == sub1_cat)
                    sub2_categories = category_df[sub2_mask]["sub2"].dropna().unique()

                    for sub2_cat in sub2_categories:
                        self.category_hierarchy[main_cat]["sub1"][sub1_cat]["sub2"][sub2_cat] = {"sub3": set()}

                        # sub2에 속하는 sub3 카테고리들 찾기
                        sub3_mask = (
                            (category_df["main"] == main_cat) & (category_df["sub1"] == sub1_cat) & (category_df["sub2"] == sub2_cat)
                        )
                        sub3_categories = category_df[sub3_mask]["sub3"].dropna().unique()

                        self.category_hierarchy[main_cat]["sub1"][sub1_cat]["sub2"][sub2_cat]["sub3"].update(sub3_categories)

        except Exception as e:
            logger.error(f"Error loading hierarchical category data: {e!s}")
            raise

    def _build_category_hierarchy(self, df: pd.DataFrame):
        """기본 카테고리 계층 구조 구축"""
        self.category_hierarchy = defaultdict(
            lambda: {"sub1": set(), "sub2": set(), "sub3": set(), "related": set(), "common_patterns": set()}
        )

        # 모든 카테고리 정보 로깅을 위한 데이터 수집
        all_categories = {"main": [], "sub1": defaultdict(list), "sub2": defaultdict(list), "sub3": defaultdict(list)}

        # 기본 계층 구조 구축
        for _, row in df.iterrows():
            main_cat = row["main"]
            if main_cat not in all_categories["main"]:
                all_categories["main"].append(main_cat)

            if pd.notna(row["sub1"]):
                self.category_hierarchy[main_cat]["sub1"].add(row["sub1"])
                all_categories["sub1"][main_cat].append(row["sub1"])
            if pd.notna(row["sub2"]):
                self.category_hierarchy[main_cat]["sub2"].add(row["sub2"])
                all_categories["sub2"][main_cat].append(row["sub2"])
            if pd.notna(row["sub3"]):
                self.category_hierarchy[main_cat]["sub3"].add(row["sub3"])
                all_categories["sub3"][main_cat].append(row["sub3"])

        # 상세 카테고리 정보 로깅
        logger.info("\nDetailed Category Information:")
        logger.info(f"Main Categories ({len(all_categories['main'])}):")
        for main in sorted(all_categories["main"]):
            sub1_count = len(set(all_categories["sub1"][main]))
            sub2_count = len(set(all_categories["sub2"][main]))
            sub3_count = len(set(all_categories["sub3"][main]))
            logger.info(f"- {main}: {sub1_count} sub1, {sub2_count} sub2, {sub3_count} sub3")

    def _extract_common_patterns(self, products: pd.Series) -> set[str]:
        """제품명에서 공통 패턴 추출"""
        words = " ".join(products.astype(str)).split()
        word_freq = pd.Series(words).value_counts()
        common_patterns = set(word_freq[word_freq >= len(products) * 0.1].index)
        return common_patterns

    def _analyze_patterns_from_trends(self):
        """트렌드 데이터를 기반으로 카테고리별 패턴 분석"""
        # 카테고리별로 제품 그룹화
        category_products = defaultdict(list)
        for product in self.trend_products:
            category_products[product["category"]].append(product["product_name"])

        # 각 카테고리별 패턴 분석
        for category, products in category_products.items():
            if category in self.category_hierarchy:
                patterns = self._extract_common_patterns(pd.Series(products))
                self.category_hierarchy[category]["common_patterns"] = patterns

    def _build_example_cases_from_trends(self):
        """트렌드 데이터를 기반으로 Few-shot 학습 예제 구축"""
        # 카테고리별로 제품 그룹화
        category_products = defaultdict(list)
        for product in self.trend_products:
            category_products[product["category"]].append({"product_name": product["product_name"], "category": product["category"]})

        # 각 카테고리별 예제 구축
        self.example_cases = {}
        for category, products in category_products.items():
            if category in self.categories["main"]:
                self.example_cases[category] = []
                # 각 카테고리당 최대 3개 예제 선택
                for product in products[:3]:
                    example = {
                        "input": product["product_name"],
                        "category": category,
                        "subcategory": None,
                        "reasoning": f"제품명 '{product['product_name']}'은(는) {category} 카테고리의 특징을 가짐",
                    }
                    self.example_cases[category].append(example)

    def save_category_result(self, result: CategoryResult):
        """카테고리 분류 결과를 Supabase에 저장"""
        try:
            data = result.to_dict()
            self.supabase.table("order_product").insert(data).execute()
            logger.info(f"Saved category result for: {result.text}")
        except Exception as e:
            logger.error(f"Error saving category result: {e!s}")

    def _create_few_shot_prompt(self, input_text: str, level: str, valid_categories: set[str] | None = None) -> str:
        """Few-shot 예제가 포함된 프롬프트 생성"""
        categories = valid_categories if valid_categories else self.categories[level]
        categories_str = "\n".join(f"- {cat}" for cat in categories)

        # 대표적인 예제 선택
        examples = []
        for cat in categories:
            if cat in self.example_cases:
                examples.extend(self.example_cases[cat][:1])

        examples_str = "\n\n".join(
            f'Input: "{example["input"]}"\n' f'Category: {example["category"]}\n' f"Confidence: 0.95\n" f'Reasoning: {example["reasoning"]}'
            for example in examples[:3]
        )

        return f"""[Task] Match the Korean product to the most appropriate category.

[Examples]
{examples_str}

[Guidelines]
- 제품의 주요 기능과 용도에 집중
- 한글/영문 제품 용어 모두 고려
- 확실하지 않은 경우 상위 카테고리 선택
- 제공된 카테고리 목록에서만 선택
- 적절한 카테고리가 없으면 'None' 출력

[Available {level} Categories]
{categories_str}

[Input]
"{input_text}"

[Output Format]
Category: [정확한 카테고리명 또는 None]
Confidence: [0.5-1.0]
Reasoning: [분류 근거 설명]"""

    def _parse_response(self, response: str, level: str, valid_categories: set[str] | None = None) -> dict:
        """LLM 응답을 파싱하여 결과 딕셔너리 반환"""
        try:
            # 정규식을 사용하여 응답에서 필요한 정보 추출
            category_match = self._regex_patterns["category"].search(response)
            confidence_match = self._regex_patterns["confidence"].search(response)
            reasoning_match = self._regex_patterns["reasoning"].search(response)

            category = category_match.group(1) if category_match else None
            confidence = float(confidence_match.group(1)) if confidence_match else 0.0
            reasoning = reasoning_match.group(1) if reasoning_match else ""

            # 카테고리가 유효한지 확인
            if valid_categories and category not in valid_categories:
                category = None
                confidence = 0.0

            return {
                "category": category,
                "confidence": confidence,
                "reasoning": reasoning,
                "success": category is not None and confidence > 0.5,
            }
        except Exception as e:
            logger.error(f"Error parsing response: {e!s}")
            return {"category": None, "confidence": 0.0, "reasoning": "", "success": False}

    def _find_matching_category(self, input_text: str, level: str, valid_categories: set[str] | None = None) -> dict:
        """Few-shot 학습을 적용한 카테고리 매칭"""
        prompt = self._create_few_shot_prompt(input_text, level, valid_categories)

        try:
            response = self.client.chat.completions.create(
                model="solar-pro", max_tokens=200, temperature=0.7, messages=[{"role": "user", "content": prompt}]
            )

            result = response.choices[0].message.content
            parsed_result = self._parse_response(result, level, valid_categories)

            if "category" in parsed_result:
                parsed_result["main"] = parsed_result.pop("category")

            return parsed_result

        except Exception as e:
            logger.error(f"Error in finding category for '{input_text}': {e!s}")
            return {"main": None, "confidence": 0.0, "success": False}

    def _find_category_by_hierarchy(self, input_text: str) -> dict:
        """계층 구조 기반 카테고리 매칭"""
        best_match = None
        max_similarity = 0

        words = set(input_text.split())

        for category, info in self.category_hierarchy.items():
            patterns = info["common_patterns"]
            if not patterns:
                continue

            similarity = len(words & patterns) / len(patterns)

            if similarity > max_similarity:
                max_similarity = similarity
                best_match = category

        return {
            "main": best_match,
            "confidence": max_similarity if max_similarity > 0.3 else 0.0,
            "success": max_similarity > 0.3,
        }

    def find_category(self, product_info: dict) -> CategoryResult:
        """계층적 구조를 고려한 카테고리 검색

        Args:
            product_info (dict): 제품 정보 딕셔너리 {'product_name': str, 'category': str}

        Returns:
            CategoryResult: 카테고리 분류 결과
        """
        input_text = f"{product_info['product_name']} ({product_info['category']})"
        logger.info(f"Finding category for: {input_text}")

        # 먼저 main 카테고리 찾기
        main_result = self._find_matching_category(input_text, "main")
        logger.info(f"Main category result: {main_result}")

        if not main_result["success"]:
            return CategoryResult(text=input_text, main=None, confidence=0.0, success=False)

        main_category = main_result["main"]

        # main 카테고리가 있으면, 해당 main에 속하는 sub1 중에서 찾기
        valid_sub1s = set(self.category_hierarchy[main_category]["sub1"].keys())
        sub1_result = self._find_matching_category(input_text, "sub1", valid_categories=valid_sub1s)
        logger.info(f"Sub1 category result: {sub1_result}")

        if not sub1_result["success"]:
            return CategoryResult(text=input_text, main=main_category, confidence=main_result["confidence"], success=True)

        sub1_category = sub1_result["main"]

        # sub1이 있으면, 해당 sub1에 속하는 sub2 중에서 찾기
        valid_sub2s = set(self.category_hierarchy[main_category]["sub1"][sub1_category]["sub2"].keys())
        sub2_result = self._find_matching_category(input_text, "sub2", valid_categories=valid_sub2s)
        logger.info(f"Sub2 category result: {sub2_result}")

        if not sub2_result["success"]:
            return CategoryResult(
                text=input_text,
                main=main_category,
                sub1=sub1_category,
                confidence=min(main_result["confidence"], sub1_result["confidence"]),
                success=True,
            )

        sub2_category = sub2_result["main"]

        # sub2가 있으면, 해당 sub2에 속하는 sub3 중에서 찾기
        valid_sub3s = self.category_hierarchy[main_category]["sub1"][sub1_category]["sub2"][sub2_category]["sub3"]
        sub3_result = self._find_matching_category(input_text, "sub3", valid_categories=valid_sub3s)
        logger.info(f"Sub3 category result: {sub3_result}")

        final_confidence = min(
            main_result["confidence"],
            sub1_result["confidence"],
            sub2_result["confidence"],
            sub3_result["confidence"] if sub3_result["success"] else 1.0,
        )

        return CategoryResult(
            text=input_text,
            main=main_category,
            sub1=sub1_category,
            sub2=sub2_category,
            sub3=sub3_result["main"] if sub3_result["success"] else None,
            confidence=final_confidence,
            success=True,
            ensemble_info={"main_result": main_result, "sub1_result": sub1_result, "sub2_result": sub2_result, "sub3_result": sub3_result},
        )
