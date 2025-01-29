import pickle
import sqlite3

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.decomposition import PCA


class EmbeddingAnalyzer:
    def __init__(self, db_path="category_embeddings.db"):
        self.db_path = db_path

    def get_all_embeddings(self):
        """데이터베이스에서 모든 임베딩 가져오기"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT main, sub1, sub2, sub3, embedding FROM category_hierarchy")
        results = cursor.fetchall()

        categories = []
        embeddings = []
        for main, sub1, sub2, sub3, emb_blob in results:
            # 카테고리 경로 생성
            path = main
            if sub1:
                path += f" > {sub1}"
            if sub2:
                path += f" > {sub2}"
            if sub3:
                path += f" > {sub3}"

            categories.append({"path": path, "main": main, "sub1": sub1, "sub2": sub2, "sub3": sub3})
            embeddings.append(pickle.loads(emb_blob))

        conn.close()
        return categories, np.array(embeddings)

    def analyze_embeddings(self):
        """임베딩 기본 통계 분석"""
        categories, embeddings = self.get_all_embeddings()

        stats = {
            "차원 수": embeddings.shape[1],
            "카테고리 수": len(embeddings),
            "값 범위": {
                "최소": float(embeddings.min()),
                "최대": float(embeddings.max()),
                "평균": float(embeddings.mean()),
                "표준편차": float(embeddings.std()),
            },
        }

        # 메인 카테고리별 통계
        main_categories = pd.DataFrame(categories)["main"].value_counts()

        return stats, main_categories

    def visualize_embeddings(self):
        """PCA를 사용하여 임베딩을 2D로 시각화"""
        categories, embeddings = self.get_all_embeddings()

        # PCA로 차원 축소
        pca = PCA(n_components=2)
        embeddings_2d = pca.fit_transform(embeddings)

        # 데이터프레임 생성
        df = pd.DataFrame(
            {
                "x": embeddings_2d[:, 0],
                "y": embeddings_2d[:, 1],
                "main": [cat["main"] for cat in categories],
                "path": [cat["path"] for cat in categories],
            }
        )

        # 시각화
        plt.figure(figsize=(12, 8))
        sns.scatterplot(data=df, x="x", y="y", hue="main", alpha=0.6)
        plt.title("Category Embeddings Visualization (PCA)")
        plt.xlabel("First Principal Component")
        plt.ylabel("Second Principal Component")
        plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
        plt.tight_layout()
        plt.show()

        return df

    def visualize_similarity_matrix(self, n_categories=20):
        """상위 n개 카테고리 간의 유사도 매트릭스 시각화"""
        categories, embeddings = self.get_all_embeddings()

        # 처음 n개의 카테고리만 선택
        selected_categories = [cat["path"] for cat in categories[:n_categories]]
        selected_embeddings = embeddings[:n_categories]

        # 코사인 유사도 계산
        similarity_matrix = np.zeros((n_categories, n_categories))
        for i in range(n_categories):
            for j in range(n_categories):
                similarity_matrix[i, j] = np.dot(selected_embeddings[i], selected_embeddings[j]) / (
                    np.linalg.norm(selected_embeddings[i]) * np.linalg.norm(selected_embeddings[j])
                )

        # 히트맵 시각화
        plt.figure(figsize=(15, 12))
        sns.heatmap(similarity_matrix, xticklabels=selected_categories, yticklabels=selected_categories, cmap="coolwarm")
        plt.title("Category Similarity Matrix")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.show()


def main():
    analyzer = EmbeddingAnalyzer()

    # 1. 기본 통계 분석
    stats, main_categories = analyzer.analyze_embeddings()
    print("\n=== 임베딩 통계 ===")
    print(pd.json_normalize(stats).to_string())

    print("\n=== 메인 카테고리별 항목 수 ===")
    print(main_categories)

    # 2. 임베딩 시각화
    print("\n=== 임베딩 시각화 생성 중... ===")
    analyzer.visualize_embeddings()

    # 3. 유사도 매트릭스 시각화
    print("\n=== 유사도 매트릭스 생성 중... ===")
    analyzer.visualize_similarity_matrix(n_categories=15)


if __name__ == "__main__":
    main()
