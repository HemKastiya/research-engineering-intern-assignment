"use client";

import { useEffect, useRef, useCallback } from "react";
import Graph from "graphology";
import Sigma from "sigma";
import { NetworkNode, NetworkEdge, NetworkGraphType } from "@/types";
import EmptyState from "@/components/ui/EmptyState";

const COMMUNITY_COLORS = [
  "#C41E1E", "#2563EB", "#16A34A", "#D97706",
  "#7C3AED", "#0891B2", "#DB2777", "#65A30D",
];

interface NetworkGraphProps {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  graphType: NetworkGraphType;
  onNodeClick?: (nodeId: string) => void;
  isLoading?: boolean;
}

export default function NetworkGraph({ nodes, edges, graphType, onNodeClick }: NetworkGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sigmaRef = useRef<Sigma | null>(null);

  const buildGraph = useCallback(() => {
    if (!containerRef.current || !nodes.length) return;

    // Cleanup previous instance
    if (sigmaRef.current) {
      sigmaRef.current.kill();
      sigmaRef.current = null;
    }

    const graph = new Graph({ multi: false });

    nodes.forEach((node) => {
      const size = Math.max(4, Math.min(32, (node.pagerank_score ?? 0.01) * 60));
      graph.addNode(node.id, {
        label: node.label,
        size,
        color: COMMUNITY_COLORS[(node.community_id ?? 0) % COMMUNITY_COLORS.length],
        x: Math.random() * 400,
        y: Math.random() * 400,
      });
    });

    const directed = graphType === "crosspost";

    edges.forEach((edge, index) => {
      try {
        if (graph.hasNode(edge.source) && graph.hasNode(edge.target)) {
          const edgeKey = `${edge.source}->${edge.target}-${index}`;
          const attrs = {
            size: Math.max(0.5, Math.min(4, edge.weight ?? 1)),
            color: "#D4CFC6",
            type: directed ? "arrow" : "line",
          };
          if (directed) {
            graph.addDirectedEdgeWithKey(edgeKey, edge.source, edge.target, attrs);
          } else {
            graph.addUndirectedEdgeWithKey(edgeKey, edge.source, edge.target, attrs);
          }
        }
      } catch {}
    });

    const renderer = new Sigma(graph, containerRef.current, {
      renderEdgeLabels: false,
      defaultEdgeColor: "#D4CFC6",
      defaultNodeColor: "#6B6860",
      labelFont: "Inter, sans-serif",
      labelSize: 11,
      labelColor: { color: "#1A1A18" },
    });

    renderer.on("clickNode", ({ node }) => {
      onNodeClick?.(node);
    });

    sigmaRef.current = renderer;
  }, [nodes, edges, graphType, onNodeClick]);

  useEffect(() => {
    buildGraph();
    return () => {
      sigmaRef.current?.kill();
      sigmaRef.current = null;
    };
  }, [buildGraph]);

  if (!nodes || nodes.length === 0) {
    return (
      <EmptyState
        title="No network data"
        description="Adjust the filters or try a different keyword to populate the graph."
      />
    );
  }

  return (
    <div
      ref={containerRef}
      className="w-full h-full rounded border border-rule bg-wash"
      style={{ minHeight: "480px" }}
    />
  );
}
