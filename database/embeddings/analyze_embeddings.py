import ast
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import seaborn as sns
from sklearn.manifold import TSNE


class AdvancedEmbeddingAnalyzer:
    def __init__(self, db_path="category_embeddings.db"):
        self.db_path = db_path
        self.output_dir = Path("embedding_analysis")
        self.output_dir.mkdir(exist_ok=True)

    def get_all_embeddings(self) -> tuple[pd.DataFrame, np.ndarray]:
        """데이터베이스에서 모든 임베딩 가져오기"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT main, sub1, sub2, sub3, embedding FROM category_hierarchy")
        results = cursor.fetchall()

        data = []
        embeddings = []
        for main, sub1, sub2, sub3, emb_blob in results:
            path = " > ".join(filter(None, [main, sub1, sub2, sub3]))
            depth = len(list(filter(None, [main, sub1, sub2, sub3])))

            data.append({"path": path, "main": main, "sub1": sub1, "sub2": sub2, "sub3": sub3, "depth": depth})
            embeddings.append(ast.literal_eval(emb_blob))
        conn.close()
        return pd.DataFrame(data), np.array(embeddings)

    def analyze_embeddings(self) -> dict:
        """임베딩 상세 분석"""
        categories_df, embeddings = self.get_all_embeddings()

        # 기본 통계
        basic_stats = {
            "차원 수": embeddings.shape[1],
            "카테고리 수": len(embeddings),
            "값 범위": {
                "최소": float(embeddings.min()),
                "최대": float(embeddings.max()),
                "평균": float(embeddings.mean()),
                "표준편차": float(embeddings.std()),
            },
        }

        # 카테고리 분석
        category_stats = {
            "메인 카테고리 수": categories_df["main"].nunique(),
            "총 카테고리 경로 수": len(categories_df),
            "depth별 카테고리 수": categories_df["depth"].value_counts().to_dict(),
            "서브카테고리 통계": {
                "sub1 수": categories_df["sub1"].nunique(),
                "sub2 수": categories_df["sub2"].nunique(),
                "sub3 수": categories_df["sub3"].nunique(),
            },
        }

        # 메인 카테고리별 서브카테고리 분포
        main_category_stats = categories_df.groupby("main").agg({"sub1": "nunique", "sub2": "nunique", "sub3": "nunique"}).to_dict()

        return {"basic_stats": basic_stats, "category_stats": category_stats, "main_category_stats": main_category_stats}

    def plot_category_distribution(self, categories_df: pd.DataFrame):
        """카테고리 분포 시각화"""
        plt.figure(figsize=(15, 10))

        # 메인 카테고리별 항목 수
        main_counts = categories_df["main"].value_counts()

        # 막대 그래프 생성
        bars = plt.bar(range(len(main_counts)), main_counts.values)

        # 축 레이블 설정
        plt.xticks(range(len(main_counts)), main_counts.index, rotation=45, ha="right")
        plt.xlabel("Main Category")
        plt.ylabel("Number of Items")
        plt.title("Distribution of Items across Main Categories")

        # 값 레이블 추가
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width() / 2.0, height, f"{int(height)}", ha="center", va="bottom")

        plt.tight_layout()
        plt.savefig(self.output_dir / "category_distribution.png")
        plt.close()

    def plot_depth_distribution(self, categories_df: pd.DataFrame):
        """카테고리 깊이 분포 시각화"""
        plt.figure(figsize=(10, 6))

        depth_counts = categories_df["depth"].value_counts().sort_index()
        bars = plt.bar(depth_counts.index, depth_counts.values)

        plt.xlabel("Category Depth")
        plt.ylabel("Number of Categories")
        plt.title("Distribution of Category Depths")

        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width() / 2.0, height, f"{int(height)}", ha="center", va="bottom")

        plt.tight_layout()
        plt.savefig(self.output_dir / "depth_distribution.png")
        plt.close()

    def plot_embedding_heatmap(self, embeddings: np.ndarray):
        """임베딩 값 분포 히트맵"""
        plt.figure(figsize=(15, 8))

        # 임베딩 샘플 선택 (처음 50개)
        sample_size = min(50, len(embeddings))
        sample_embeddings = embeddings[:sample_size]

        # 히트맵 생성
        sns.heatmap(sample_embeddings, cmap="coolwarm", center=0, xticklabels=False, yticklabels=False)

        plt.title("Embedding Values Heatmap (Sample)")
        plt.xlabel("Embedding Dimensions")
        plt.ylabel("Categories")

        plt.tight_layout()
        plt.savefig(self.output_dir / "embedding_heatmap.png")
        plt.close()

    def plot_interactive_tsne(self, categories_df: pd.DataFrame, embeddings: np.ndarray):
        """t-SNE를 사용한 인터랙티브 시각화"""
        # t-SNE 차원 축소
        tsne = TSNE(n_components=2, random_state=42)
        embeddings_2d = tsne.fit_transform(embeddings)

        # Plotly 시각화
        fig = px.scatter(
            x=embeddings_2d[:, 0],
            y=embeddings_2d[:, 1],
            color=categories_df["main"],
            hover_data={"path": categories_df["path"], "main": categories_df["main"]},
            title="t-SNE Visualization of Category Embeddings",
        )

        fig.write_html(self.output_dir / "tsne_visualization.html")

    def generate_report(self):
        """분석 리포트 생성"""
        categories_df, embeddings = self.get_all_embeddings()
        analysis_results = self.analyze_embeddings()

        # 모든 시각화 생성
        self.plot_category_distribution(categories_df)
        self.plot_depth_distribution(categories_df)
        self.plot_embedding_heatmap(embeddings)
        self.plot_interactive_tsne(categories_df, embeddings)

        # 마크다운 리포트 생성
        report = f"""# Embedding Analysis Report

## Basic Statistics
- Dimensions: {analysis_results["basic_stats"]["차원 수"]}
- Total Categories: {analysis_results["basic_stats"]["카테고리 수"]}
- Value Range:
  - Min: {analysis_results["basic_stats"]["값 범위"]["최소"]:.6f}
  - Max: {analysis_results["basic_stats"]["값 범위"]["최대"]:.6f}
  - Mean: {analysis_results["basic_stats"]["값 범위"]["평균"]:.6f}
  - Std: {analysis_results["basic_stats"]["값 범위"]["표준편차"]:.6f}

## Category Statistics
- Main Categories: {analysis_results["category_stats"]["메인 카테고리 수"]}
- Total Category Paths: {analysis_results["category_stats"]["총 카테고리 경로 수"]}
- Subcategories:
  - Sub1: {analysis_results["category_stats"]["서브카테고리 통계"]["sub1 수"]}
  - Sub2: {analysis_results["category_stats"]["서브카테고리 통계"]["sub2 수"]}
  - Sub3: {analysis_results["category_stats"]["서브카테고리 통계"]["sub3 수"]}

## Category Depth Distribution
{pd.Series(analysis_results["category_stats"]["depth별 카테고리 수"]).to_markdown()}

## Main Categories Analysis
{categories_df["main"].value_counts().to_markdown()}

## Visualizations
The following visualizations have been generated:
1. Category Distribution (category_distribution.png)
2. Depth Distribution (depth_distribution.png)
3. Embedding Heatmap (embedding_heatmap.png)
4. Interactive t-SNE Visualization (tsne_visualization.html)
"""

        with open(self.output_dir / "analysis_report.md", "w", encoding="utf-8") as f:
            f.write(report)


def main():
    analyzer = AdvancedEmbeddingAnalyzer()
    analyzer.generate_report()
    print(f"Analysis completed. Results saved in '{analyzer.output_dir}' directory.")


if __name__ == "__main__":
    main()
