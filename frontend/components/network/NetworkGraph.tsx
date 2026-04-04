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
  const nodePositionRef = useRef<Record<string, { x: number; y: number }>>({});
  const draggedNodeRef = useRef<string | null>(null);
  const draggedDuringPointerRef = useRef(false);
  const ignoreNextClickRef = useRef(false);

  const buildGraph = useCallback(() => {
    if (!containerRef.current || !nodes.length) return;

    // Cleanup previous instance
    if (sigmaRef.current) {
      sigmaRef.current.kill();
      sigmaRef.current = null;
    }

    const graph = new Graph({ multi: false });
    const nextPositions: Record<string, { x: number; y: number }> = {};

    nodes.forEach((node) => {
      const size = Math.max(4, Math.min(32, (node.pagerank_score ?? 0.01) * 60));
      const existing = nodePositionRef.current[node.id];
      const position = existing ?? {
        x: Math.random() * 400,
        y: Math.random() * 400,
      };
      nextPositions[node.id] = position;
      graph.addNode(node.id, {
        label: node.label,
        size,
        color: COMMUNITY_COLORS[(node.community_id ?? 0) % COMMUNITY_COLORS.length],
        x: position.x,
        y: position.y,
      });
    });
    nodePositionRef.current = nextPositions;

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
      minCameraRatio: 0.2,
      maxCameraRatio: 3,
      zoomingRatio: 1.5,
      enableCameraZooming: true,
      enableCameraPanning: true,
    });

    renderer.on("clickNode", ({ node }) => {
      if (ignoreNextClickRef.current) {
        ignoreNextClickRef.current = false;
        return;
      }
      onNodeClick?.(node);
    });

    renderer.on("downNode", ({ node }) => {
      draggedNodeRef.current = node;
      draggedDuringPointerRef.current = false;
      renderer.getCamera().disable();
      if (containerRef.current) containerRef.current.style.cursor = "grabbing";
    });

    renderer.getMouseCaptor().on("mousemovebody", (event) => {
      const draggedNode = draggedNodeRef.current;
      if (!draggedNode) return;

      const graphPosition = renderer.viewportToGraph(event);
      graph.setNodeAttribute(draggedNode, "x", graphPosition.x);
      graph.setNodeAttribute(draggedNode, "y", graphPosition.y);
      nodePositionRef.current[draggedNode] = { x: graphPosition.x, y: graphPosition.y };
      draggedDuringPointerRef.current = true;

      event.preventSigmaDefault();
      if (event.original?.preventDefault) event.original.preventDefault();
      if (event.original?.stopPropagation) event.original.stopPropagation();
    });

    renderer.getMouseCaptor().on("mouseup", () => {
      renderer.getCamera().enable();
      draggedNodeRef.current = null;
      if (containerRef.current) containerRef.current.style.cursor = "grab";
      if (draggedDuringPointerRef.current) {
        ignoreNextClickRef.current = true;
      }
    });

    renderer.on("enterNode", () => {
      if (!draggedNodeRef.current && containerRef.current) {
        containerRef.current.style.cursor = "grab";
      }
    });

    renderer.on("leaveNode", () => {
      if (!draggedNodeRef.current && containerRef.current) {
        containerRef.current.style.cursor = "default";
      }
    });

    sigmaRef.current = renderer;
  }, [nodes, edges, graphType, onNodeClick]);

  const zoomIn = useCallback(() => {
    sigmaRef.current?.getCamera().animatedZoom();
  }, []);

  const zoomOut = useCallback(() => {
    sigmaRef.current?.getCamera().animatedUnzoom();
  }, []);

  const resetView = useCallback(() => {
    sigmaRef.current?.getCamera().animatedReset();
  }, []);

  useEffect(() => {
    buildGraph();
    return () => {
      sigmaRef.current?.kill();
      sigmaRef.current = null;
      draggedNodeRef.current = null;
      ignoreNextClickRef.current = false;
      draggedDuringPointerRef.current = false;
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
    <div className="relative w-full h-full">
      <div
        ref={containerRef}
        className="w-full h-full rounded border border-rule bg-wash"
        style={{ minHeight: "480px" }}
      />

      <div className="absolute right-3 top-3 flex flex-col gap-2">
        <button onClick={zoomIn} className="press-btn press-btn-ghost px-3 py-1 text-xs" title="Zoom in">
          +
        </button>
        <button onClick={zoomOut} className="press-btn press-btn-ghost px-3 py-1 text-xs" title="Zoom out">
          -
        </button>
        <button onClick={resetView} className="press-btn press-btn-ghost px-3 py-1 text-xs" title="Reset view">
          Reset
        </button>
      </div>

      <p className="byline absolute bottom-3 left-3 rounded bg-paper/80 px-2 py-1">
        Drag nodes to reposition. Scroll to zoom.
      </p>
    </div>
  );
}
