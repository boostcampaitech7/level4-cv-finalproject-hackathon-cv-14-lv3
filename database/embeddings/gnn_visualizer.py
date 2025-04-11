import json
import sqlite3
from base64 import b64decode
from pathlib import Path
from typing import Any

import community.community_louvain as community_louvain
import networkx as nx
import numpy as np
import pandas as pd
from pyvis.network import Network


class GraphCategoryVisualizer:
    def __init__(self, db_path: str = "category_embeddings.db"):
        self.db_path = db_path
        self.output_dir = Path("embedding_analysis")
        self.output_dir.mkdir(exist_ok=True)

    def deserialize_embedding(self, data: bytes) -> np.ndarray:
        """Convert base64 encoded bytes back to numpy array"""
        return np.frombuffer(b64decode(data))

    def get_category_data(self) -> pd.DataFrame:
        """Get category data from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT main, sub1, sub2, sub3, embedding FROM category_hierarchy")
        results = cursor.fetchall()

        data = []
        for main, sub1, sub2, sub3, emb_blob in results:
            embedding = self.deserialize_embedding(emb_blob)
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

    def calculate_node_importance(self, graph: nx.Graph) -> dict[str, float]:
        """Calculate node importance using PageRank and degree centrality"""
        pagerank = nx.pagerank(graph)
        degree_cent = nx.degree_centrality(graph)

        importance = {}
        for node in graph.nodes():
            importance[node] = (pagerank[node] + degree_cent[node]) / 2

        return importance

    def create_category_graph(self, df: pd.DataFrame) -> nx.Graph:
        """Create hierarchical category graph"""
        graph = nx.Graph()

        edge_weights: dict[tuple[str, str], int] = {}

        for _, row in df.iterrows():
            # Add main category
            if not graph.has_node(row["main"]):
                graph.add_node(row["main"], level="main", size=25)

            # Add sub1 category
            if row["sub1"]:
                if not graph.has_node(row["sub1"]):
                    graph.add_node(row["sub1"], level="sub1", size=20)
                edge_key = tuple(sorted([row["main"], row["sub1"]]))
                edge_weights[edge_key] = edge_weights.get(edge_key, 0) + 1

            # Add sub2 category
            if row["sub2"]:
                if not graph.has_node(row["sub2"]):
                    graph.add_node(row["sub2"], level="sub2", size=15)
                edge_key = tuple(sorted([row["sub1"], row["sub2"]]))
                edge_weights[edge_key] = edge_weights.get(edge_key, 0) + 1

            # Add sub3 category
            if row["sub3"]:
                if not graph.has_node(row["sub3"]):
                    graph.add_node(row["sub3"], level="sub3", size=10)
                edge_key = tuple(sorted([row["sub2"], row["sub3"]]))
                edge_weights[edge_key] = edge_weights.get(edge_key, 0) + 1

        # Add edges with weights
        for (node1, node2), weight in edge_weights.items():
            graph.add_edge(node1, node2, weight=weight)

        return graph

    def create_interactive_graph(self, graph: nx.Graph, max_nodes: int = 1000) -> None:
        """Create interactive graph visualization"""
        if len(graph.nodes) > max_nodes:
            sampled_nodes = list(graph.nodes)[:max_nodes]
            graph = nx.Graph(graph.subgraph(sampled_nodes))

        node_importance = self.calculate_node_importance(graph)
        net = Network(height="900px", width="100%", bgcolor="#ffffff", font_color="#333333")

        communities = community_louvain.best_partition(graph)

        color_scheme = {
            "main": {"color": "#e41a1c", "border": "#8b0000", "highlight": "#ff4444"},
            "sub1": {"color": "#377eb8", "border": "#00008b", "highlight": "#4444ff"},
            "sub2": {"color": "#4daf4a", "border": "#006400", "highlight": "#44ff44"},
            "sub3": {"color": "#984ea3", "border": "#4b0082", "highlight": "#ff44ff"},
        }

        # Add nodes
        for node in graph.nodes():
            level = graph.nodes[node]["level"]
            base_size = graph.nodes[node]["size"]
            size = base_size * (1 + node_importance[node] * 10)

            style = color_scheme.get(level, {"color": "#999999", "border": "#666666", "highlight": "#bbbbbb"})

            node_info = (
                f"Level: {level}\n"
                f"Community: {communities[node]}\n"
                f"Importance: {node_importance[node]:.3f}\n"
                f"Connected to: {graph.degree(node)} nodes"
            )

            net.add_node(node, label=node, size=size, color=style["color"], borderWidth=2, borderColor=style["border"], title=node_info)

        # Add edges
        edge_weights = nx.get_edge_attributes(graph, "weight")
        max_weight = max(edge_weights.values())

        for edge in graph.edges():
            weight = edge_weights.get(edge, 1)
            width = 1 + (weight / max_weight) * 5

            net.add_edge(edge[0], edge[1], width=width, color={"color": "#666666", "highlight": "#ff0000"})

        # Set physics options
        net.set_options("""
        {
            "nodes": {
                "font": {"size": 12, "face": "Tahoma"},
                "shapeProperties": {"borderRadius": 5}
            },
            "edges": {
                "smooth": {
                    "type": "continuous",
                    "forceDirection": "none"
                },
                "color": {"inherit": false}
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

        output_path = str(self.output_dir / "category_graph.html")
        try:
            net.write_html(output_path)
        except Exception as e:
            print(f"Failed to write HTML using write_html: {e}")
            try:
                net.show(output_path)
            except Exception as e:
                print(f"Failed to show network: {e}")
                try:
                    html_string = net.generate_html()
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(html_string)
                except Exception as e:
                    print(f"Failed to write HTML file: {e}")

    def analyze_graph_metrics(self, graph: nx.Graph) -> dict[str, Any]:
        """Analyze graph metrics"""
        metrics = {
            "기본 메트릭": {
                "노드 수": len(graph.nodes),
                "엣지 수": len(graph.edges),
                "평균 연결성": sum(dict(graph.degree()).values()) / len(graph),
                "평균 클러스터링 계수": nx.average_clustering(graph),
                "연결 컴포넌트 수": nx.number_connected_components(graph),
            },
            "레벨별 통계": {
                level: sum(1 for n in graph.nodes if graph.nodes[n]["level"] == level) for level in ["main", "sub1", "sub2", "sub3"]
            },
        }

        degree_cent = nx.degree_centrality(graph)
        betweenness_cent = nx.betweenness_centrality(graph)
        pagerank = nx.pagerank(graph)

        metrics["중심성 분석"] = {
            "상위 연결 중심성": dict(sorted(degree_cent.items(), key=lambda x: x[1], reverse=True)[:10]),
            "상위 매개 중심성": dict(sorted(betweenness_cent.items(), key=lambda x: x[1], reverse=True)[:10]),
            "상위 페이지랭크": dict(sorted(pagerank.items(), key=lambda x: x[1], reverse=True)[:10]),
        }

        return metrics

    def generate_graph_report(self) -> None:
        """Generate graph analysis report"""
        print("Loading category data...")
        df = self.get_category_data()

        print("Creating category graph...")
        graph = self.create_category_graph(df)

        print("Generating enhanced interactive visualization...")
        self.create_interactive_graph(graph)

        print("Analyzing graph metrics...")
        metrics = self.analyze_graph_metrics(graph)

        report = f"""# Enhanced Category Graph Analysis Report

## Basic Metrics
{json.dumps(metrics["기본 메트릭"], indent=2, ensure_ascii=False)}

## Level Statistics
{json.dumps(metrics["레벨별 통계"], indent=2, ensure_ascii=False)}

## Centrality Analysis
{json.dumps(metrics["중심성 분석"], indent=2, ensure_ascii=False)}

## Visualizations
- Enhanced interactive graph visualization: category_graph.html
"""

        with open(self.output_dir / "graph_analysis.md", "w", encoding="utf-8") as f:
            f.write(report)

        print(f"Enhanced analysis completed. Results saved in '{self.output_dir}' directory.")


def main() -> None:
    visualizer = GraphCategoryVisualizer()
    visualizer.generate_graph_report()


if __name__ == "__main__":
    main()
