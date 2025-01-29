import json
import sqlite3
from base64 import b64decode
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.decomposition import PCA
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
            embeddings.append(self.deserialize_embedding(emb_blob))

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

        main_category_stats = categories_df.groupby("main").agg({"sub1": "nunique", "sub2": "nunique", "sub3": "nunique"}).to_dict()

        return {"basic_stats": basic_stats, "category_stats": category_stats, "main_category_stats": main_category_stats}

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
            plt.text(bar.get_x() + bar.get_width() / 2.0, height, f"{int(height)}", ha="center", va="bottom")

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
            plt.text(bar.get_x() + bar.get_width() / 2.0, height, f"{int(height)}", ha="center", va="bottom")

        plt.tight_layout()
        plt.savefig(self.output_dir / "depth_distribution.png")
        plt.close()

    def plot_embedding_heatmap(self, embeddings: np.ndarray) -> None:
        """Plot embedding values heatmap"""
        plt.figure(figsize=(15, 8))

        sample_size = min(50, len(embeddings))
        sample_embeddings = embeddings[:sample_size]

        sns.heatmap(sample_embeddings, cmap="coolwarm", center=0, xticklabels=False, yticklabels=False)

        plt.title("Embedding Values Heatmap (Sample)")
        plt.xlabel("Embedding Dimensions")
        plt.ylabel("Categories")

        plt.tight_layout()
        plt.savefig(self.output_dir / "embedding_heatmap.png")
        plt.close()

    def generate_dimensionality_reduction_plots(self, categories_df: pd.DataFrame, embeddings: np.ndarray) -> None:
        """Generate various dimensionality reduction visualizations"""
        # PCA
        pca = PCA(n_components=2)
        pca_result = pca.fit_transform(embeddings)

        plt.figure(figsize=(12, 8))
        plt.scatter(pca_result[:, 0], pca_result[:, 1], alpha=0.5)
        plt.title("PCA Visualization of Embeddings")
        plt.xlabel("First Principal Component")
        plt.ylabel("Second Principal Component")
        plt.savefig(self.output_dir / "pca_visualization.png")
        plt.close()

        # t-SNE
        tsne = TSNE(n_components=2, random_state=42)
        tsne_result = tsne.fit_transform(embeddings)

        plt.figure(figsize=(12, 8))
        scatter = plt.scatter(tsne_result[:, 0], tsne_result[:, 1], c=categories_df["depth"], cmap="viridis", alpha=0.5)
        plt.colorbar(scatter, label="Category Depth")
        plt.title("t-SNE Visualization of Embeddings")
        plt.savefig(self.output_dir / "tsne_visualization.png")
        plt.close()

    def analyze_embedding_clusters(self, embeddings: np.ndarray) -> dict:
        """Analyze embedding clusters using various metrics"""
        from sklearn.cluster import KMeans
        from sklearn.metrics import silhouette_score

        n_clusters = min(10, len(embeddings))
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        cluster_labels = kmeans.fit_predict(embeddings)

        cluster_stats = {
            "cluster_sizes": np.bincount(cluster_labels).tolist(),
            "silhouette_score": float(silhouette_score(embeddings, cluster_labels)),
            "inertia": float(kmeans.inertia_),
        }

        return cluster_stats

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
