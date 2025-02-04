import ast
import json
import sqlite3
from base64 import b64decode
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import seaborn as sns
from sklearn.manifold import TSNE


class EmbeddingAnalyzer:
    def __init__(self, db_path: str = "category_embeddings.db"):
        self.db_path = db_path
        self.output_dir = Path("embedding_analysis")
        self.output_dir.mkdir(exist_ok=True)

    def deserialize_embedding(self, data: bytes) -> np.ndarray:
        """Convert base64 encoded bytes back to numpy array"""
        return np.frombuffer(b64decode(data))

    def get_all_embeddings(self) -> tuple[pd.DataFrame, np.ndarray]:
        """Get all embeddings from database"""
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
        """Analyze embeddings and generate statistics"""
        categories_df, embeddings = self.get_all_embeddings()

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

        return {
            "basic_stats": basic_stats,
            "category_stats": category_stats,
            "main_category_stats": main_category_stats,
        }

    def plot_category_distribution(self, categories_df: pd.DataFrame) -> None:
        """Plot category distribution"""
        plt.figure(figsize=(15, 10))

        main_counts = categories_df["main"].value_counts()

        bars = plt.bar(range(len(main_counts)), main_counts.values)

        plt.xticks(range(len(main_counts)), main_counts.index, rotation=45, ha="right")
        plt.xlabel("Main Category")
        plt.ylabel("Number of Items")
        plt.title("Distribution of Items across Main Categories")

        for bar in bars:
            height = bar.get_height()
            plt.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{int(height)}",
                ha="center",
                va="bottom",
            )

        plt.tight_layout()
        plt.savefig(self.output_dir / "category_distribution.png")
        plt.close()

    def plot_depth_distribution(self, categories_df: pd.DataFrame) -> None:
        """Plot category depth distribution"""
        plt.figure(figsize=(10, 6))

        depth_counts = categories_df["depth"].value_counts().sort_index()
        bars = plt.bar(depth_counts.index, depth_counts.values)

        plt.xlabel("Category Depth")
        plt.ylabel("Number of Categories")
        plt.title("Distribution of Category Depths")

        for bar in bars:
            height = bar.get_height()
            plt.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{int(height)}",
                ha="center",
                va="bottom",
            )

        plt.tight_layout()
        plt.savefig(self.output_dir / "depth_distribution.png")
        plt.close()

    def plot_embedding_heatmap(self, embeddings: np.ndarray) -> None:
        """Plot embedding values heatmap"""
        plt.figure(figsize=(15, 8))

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

    def generate_report(self) -> None:
        """Generate comprehensive analysis report"""
        categories_df, embeddings = self.get_all_embeddings()
        analysis_results = self.analyze_embeddings()

        # Generate visualizations
        self.plot_category_distribution(categories_df)
        self.plot_depth_distribution(categories_df)
        self.plot_embedding_heatmap(embeddings)
        self.generate_dimensionality_reduction_plots(categories_df, embeddings)

        # Analyze clusters
        cluster_results = self.analyze_embedding_clusters(embeddings)

        # Generate report
        report = f"""# Embedding Analysis Report

## Basic Statistics
{json.dumps(analysis_results["basic_stats"], indent=2, ensure_ascii=False)}

## Category Statistics
{json.dumps(analysis_results["category_stats"], indent=2, ensure_ascii=False)}

## Cluster Analysis
{json.dumps(cluster_results, indent=2, ensure_ascii=False)}

## Visualizations Generated
1. Category Distribution (category_distribution.png)
2. Depth Distribution (depth_distribution.png)
3. Embedding Heatmap (embedding_heatmap.png)
4. PCA Visualization (pca_visualization.png)
5. t-SNE Visualization (tsne_visualization.png)
"""

        with open(self.output_dir / "analysis_report.md", "w", encoding="utf-8") as f:
            f.write(report)


def main() -> None:
    analyzer = EmbeddingAnalyzer()
    print("Generating embedding analysis report...")
    analyzer.generate_report()
    print("Analysis completed. Results saved in 'embedding_analysis' directory.")


if __name__ == "__main__":
    main()
