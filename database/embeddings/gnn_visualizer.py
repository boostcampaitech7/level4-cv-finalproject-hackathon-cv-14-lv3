import json
import pickle
import sqlite3
from pathlib import Path

import community.community_louvain as community_louvain
import networkx as nx
import pandas as pd
from pyvis.network import Network


class EnhancedGraphVisualizer:
    def __init__(self, db_path="category_embeddings.db"):
        self.db_path = db_path
        self.output_dir = Path("embedding_analysis")
        self.output_dir.mkdir(exist_ok=True)

    def get_category_data(self) -> pd.DataFrame:
        """데이터베이스에서 카테고리 데이터 가져오기"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT main, sub1, sub2, sub3, embedding FROM category_hierarchy")
        results = cursor.fetchall()

        data = []
        for main, sub1, sub2, sub3, emb_blob in results:
            embedding = pickle.loads(emb_blob)
            data.append(
                {
                    "main": main,
                    "sub1": sub1 if sub1 else None,
                    "sub2": sub2 if sub2 else None,
                    "sub3": sub3 if sub3 else None,
                    "embedding": embedding,
                }
            )

        conn.close()
        return pd.DataFrame(data)

    def calculate_node_importance(self, G: nx.Graph) -> dict[str, float]:
        """노드 중요도 계산"""
        # 페이지랭크와 연결 중심성을 결합
        pagerank = nx.pagerank(G)
        degree_cent = nx.degree_centrality(G)

        importance = {}
        for node in G.nodes():
            importance[node] = (pagerank[node] + degree_cent[node]) / 2

        return importance

    def create_category_graph(self, df: pd.DataFrame) -> nx.Graph:
        """개선된 카테고리 그래프 생성"""
        G = nx.Graph()

        # 엣지 가중치를 저장할 딕셔너리
        edge_weights = {}

        for _, row in df.iterrows():
            # Main 카테고리 추가
            if not G.has_node(row["main"]):
                G.add_node(row["main"], level="main", size=25)

            # Sub1 카테고리 추가
            if row["sub1"]:
                if not G.has_node(row["sub1"]):
                    G.add_node(row["sub1"], level="sub1", size=20)
                edge_key = tuple(sorted([row["main"], row["sub1"]]))
                edge_weights[edge_key] = edge_weights.get(edge_key, 0) + 1

            # Sub2 카테고리 추가
            if row["sub2"]:
                if not G.has_node(row["sub2"]):
                    G.add_node(row["sub2"], level="sub2", size=15)
                edge_key = tuple(sorted([row["sub1"], row["sub2"]]))
                edge_weights[edge_key] = edge_weights.get(edge_key, 0) + 1

            # Sub3 카테고리 추가
            if row["sub3"]:
                if not G.has_node(row["sub3"]):
                    G.add_node(row["sub3"], level="sub3", size=10)
                edge_key = tuple(sorted([row["sub2"], row["sub3"]]))
                edge_weights[edge_key] = edge_weights.get(edge_key, 0) + 1

        # 엣지 추가 (가중치 포함)
        for (node1, node2), weight in edge_weights.items():
            G.add_edge(node1, node2, weight=weight)

        return G

    def create_interactive_graph(self, G: nx.Graph, max_nodes: int = 1000):
        """개선된 인터랙티브 그래프 시각화"""
        if len(G.nodes) > max_nodes:
            G = nx.Graph(G.subgraph(list(G.nodes)[:max_nodes]))

        # 노드 중요도 계산
        node_importance = self.calculate_node_importance(G)

        # Pyvis 네트워크 생성
        net = Network(height="900px", width="100%", bgcolor="#ffffff", font_color="#333333")

        # 커뮤니티 탐지
        communities = community_louvain.best_partition(G)

        # 노드 추가
        for node in G.nodes():
            level = G.nodes[node]["level"]
            base_size = G.nodes[node]["size"]

            # 노드 크기를 중요도에 따라 조정
            size = base_size * (1 + node_importance[node] * 10)

            # 레벨별 색상 및 스타일
            color_scheme = {
                "main": {"color": "#e41a1c", "border": "#8b0000", "highlight": "#ff4444"},
                "sub1": {"color": "#377eb8", "border": "#00008b", "highlight": "#4444ff"},
                "sub2": {"color": "#4daf4a", "border": "#006400", "highlight": "#44ff44"},
                "sub3": {"color": "#984ea3", "border": "#4b0082", "highlight": "#ff44ff"},
            }

            style = color_scheme.get(level, {"color": "#999999", "border": "#666666", "highlight": "#bbbbbb"})

            # 노드 정보 포맷팅
            node_info = f"""
            Level: {level}
            Community: {communities[node]}
            Importance: {node_importance[node]:.3f}
            Connected to: {G.degree(node)} nodes
            """

            net.add_node(node, label=node, size=size, color=style["color"], borderWidth=2, borderColor=style["border"], title=node_info)

        # 엣지 추가 (가중치 기반 스타일링)
        edge_weights = nx.get_edge_attributes(G, "weight")
        max_weight = max(edge_weights.values())

        for edge in G.edges():
            weight = edge_weights.get(edge, 1)
            width = 1 + (weight / max_weight) * 5

            net.add_edge(edge[0], edge[1], width=width, color={"color": "#666666", "highlight": "#ff0000"})

        # 물리 시뮬레이션 및 인터랙션 설정
        net.set_options("""
        var options = {
            "nodes": {
                "font": {
                    "size": 12,
                    "face": "Tahoma"
                },
                "shapeProperties": {
                    "borderRadius": 5
                }
            },
            "edges": {
                "smooth": {
                    "type": "continuous",
                    "forceDirection": "none"
                },
                "color": {
                    "inherit": false
                }
            },
            "physics": {
                "barnesHut": {
                    "gravitationalConstant": -2000,
                    "centralGravity": 0.3,
                    "springLength": 150,
                    "springConstant": 0.04
                },
                "maxVelocity": 50,
                "minVelocity": 0.1,
                "solver": "barnesHut",
                "stabilization": {
                    "enabled": true,
                    "iterations": 1000
                }
            },
            "interaction": {
                "hover": true,
                "navigationButtons": true,
                "keyboard": true,
                "tooltipDelay": 100,
                "hideEdgesOnDrag": true,
                "hideEdgesOnZoom": true
            }
        }
        """)

        # HTML 파일로 저장
        output_path = str(self.output_dir / "category_graph.html")
        try:
            net.write_html(output_path)
        except AttributeError:
            try:
                net.show(output_path)
            except:
                html_string = net.generate_html()
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(html_string)

    def analyze_graph_metrics(self, G: nx.Graph) -> dict:
        """확장된 그래프 메트릭 분석"""
        metrics = {
            "기본 메트릭": {
                "노드 수": len(G.nodes),
                "엣지 수": len(G.edges),
                "평균 연결성": sum(dict(G.degree()).values()) / len(G),
                "평균 클러스터링 계수": nx.average_clustering(G),
                "연결 컴포넌트 수": nx.number_connected_components(G),
            },
            "레벨별 통계": {level: sum(1 for n in G.nodes if G.nodes[n]["level"] == level) for level in ["main", "sub1", "sub2", "sub3"]},
        }

        # 중심성 메트릭
        degree_cent = nx.degree_centrality(G)
        betweenness_cent = nx.betweenness_centrality(G)
        pagerank = nx.pagerank(G)

        metrics["중심성 분석"] = {
            "상위 연결 중심성": dict(sorted(degree_cent.items(), key=lambda x: x[1], reverse=True)[:10]),
            "상위 매개 중심성": dict(sorted(betweenness_cent.items(), key=lambda x: x[1], reverse=True)[:10]),
            "상위 페이지랭크": dict(sorted(pagerank.items(), key=lambda x: x[1], reverse=True)[:10]),
        }

        return metrics

    def generate_graph_report(self):
        """개선된 분석 리포트 생성"""
        print("Loading category data...")
        df = self.get_category_data()

        print("Creating category graph...")
        G = self.create_category_graph(df)

        print("Generating enhanced interactive visualization...")
        self.create_interactive_graph(G)

        print("Analyzing graph metrics...")
        metrics = self.analyze_graph_metrics(G)

        report = f"""# Enhanced Category Graph Analysis Report

## Basic Metrics
{json.dumps(metrics["기본 메트릭"], indent=2, ensure_ascii=False)}

## Level Statistics
{json.dumps(metrics["레벨별 통계"], indent=2, ensure_ascii=False)}

## Centrality Analysis
{json.dumps(metrics["중심성 분석"], indent=2, ensure_ascii=False)}

## Visualizations
- Enhanced interactive graph visualization: enhanced_category_graph.html
"""

        with open(self.output_dir / "enhanced_graph_analysis.md", "w", encoding="utf-8") as f:
            f.write(report)

        print(f"Enhanced analysis completed. Results saved in '{self.output_dir}' directory.")


def main():
    visualizer = EnhancedGraphVisualizer()
    visualizer.generate_graph_report()


if __name__ == "__main__":
    main()
