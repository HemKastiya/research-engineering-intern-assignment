"use client";

import { useEffect, useRef, useCallback } from "react";
import Graph from "graphology";
import Sigma from "sigma";
import { NetworkNode, NetworkEdge } from "@/types";
import EmptyState from "@/components/ui/EmptyState";

const COMMUNITY_COLORS = [
  "#C41E1E", "#2563EB", "#16A34A", "#D97706",
  "#7C3AED", "#0891B2", "#DB2777", "#65A30D",
];

interface NetworkGraphProps {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  onNodeClick?: (nodeId: string) => void;
  isLoading?: boolean;
}

export default function NetworkGraph({ nodes, edges, onNodeClick }: NetworkGraphProps) {
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

    edges.forEach((edge) => {
      try {
        if (graph.hasNode(edge.source) && graph.hasNode(edge.target)) {
          graph.addEdge(edge.source, edge.target, {
            size: Math.max(0.5, Math.min(4, edge.weight ?? 1)),
            color: "#D4CFC6",
          });
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
  }, [nodes, edges, onNodeClick]);

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
        description="Adjust the filters or try a different subreddit to populate the graph."
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
