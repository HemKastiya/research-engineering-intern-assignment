"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import { getNetwork, NetworkParams } from "@/lib/api";
import { computePageRank } from "@/lib/network";
import {
  GraphResult,
  NetworkGraphType,
  NetworkNode,
} from "@/types";
import dynamic from "next/dynamic";
import GraphControls from "@/components/network/GraphControls";
import NodeSidebar from "@/components/network/NodeSidebar";
import SectionHeading from "@/components/ui/SectionHeading";
import ErrorBanner from "@/components/ui/ErrorBanner";
import LoadingSkeleton from "@/components/ui/LoadingSkeleton";

const NetworkGraph = dynamic(
  () => import("@/components/network/NetworkGraph"),
  { ssr: false, loading: () => <LoadingSkeleton variant="chart" /> }
);

const DEFAULT_GRAPH_TYPE: NetworkGraphType = "co_subreddit";
const DEFAULT_TOP_N = 150;

function emptyGraph(graphType: NetworkGraphType): GraphResult {
  return {
    nodes: [],
    edges: [],
    meta: {
      graph_type: graphType,
      query: null,
      top_n: DEFAULT_TOP_N,
      max_nodes: 200,
      total_nodes_before_limit: 0,
      total_edges_before_limit: 0,
      returned_nodes: 0,
      returned_edges: 0,
      truncated: false,
      truncation_note: null,
      corpus_hash: "",
      computed_at: "",
      backbone_computed_at: "",
    },
  };
}

function applyClientFilters(
  sourceGraph: GraphResult,
  removedNodeIds: Set<string>,
  minEdgeWeight: number,
  minDegree: number
): GraphResult {
  const activeNodes = sourceGraph.nodes.filter((node) => !removedNodeIds.has(node.id));
  const activeNodeIds = new Set(activeNodes.map((node) => node.id));

  let filteredEdges = sourceGraph.edges.filter((edge) => {
    if (edge.weight < minEdgeWeight) return false;
    return activeNodeIds.has(edge.source) && activeNodeIds.has(edge.target);
  });

  let filteredNodes = activeNodes;
  if (minDegree > 0) {
    const degreeMap = new Map<string, number>();
    filteredNodes.forEach((node) => degreeMap.set(node.id, 0));
    filteredEdges.forEach((edge) => {
      degreeMap.set(edge.source, (degreeMap.get(edge.source) ?? 0) + 1);
      degreeMap.set(edge.target, (degreeMap.get(edge.target) ?? 0) + 1);
    });

    const keepNodes = new Set(
      Array.from(degreeMap.entries())
        .filter(([, degree]) => degree >= minDegree)
        .map(([nodeId]) => nodeId)
    );

    filteredNodes = filteredNodes.filter((node) => keepNodes.has(node.id));
    filteredEdges = filteredEdges.filter(
      (edge) => keepNodes.has(edge.source) && keepNodes.has(edge.target)
    );
  }

  const recomputedPageRank = computePageRank(
    filteredNodes.map((node) => node.id),
    filteredEdges,
    sourceGraph.meta.graph_type
  );

  const nodesWithUpdatedRank = filteredNodes
    .map((node) => ({
      ...node,
      pagerank_score: recomputedPageRank[node.id] ?? 0,
    }))
    .sort((left, right) => right.pagerank_score - left.pagerank_score);

  return {
    ...sourceGraph,
    nodes: nodesWithUpdatedRank,
    edges: filteredEdges,
    meta: {
      ...sourceGraph.meta,
      returned_nodes: nodesWithUpdatedRank.length,
      returned_edges: filteredEdges.length,
      computed_at: new Date().toISOString(),
    },
  };
}

export default function NetworkPage() {
  const [keywordInput, setKeywordInput] = useState("");
  const [keywordQuery, setKeywordQuery] = useState("");
  const [graphType, setGraphType] = useState<NetworkGraphType>(DEFAULT_GRAPH_TYPE);
  const [topN, setTopN] = useState(DEFAULT_TOP_N);
  const [minEdgeWeight, setMinEdgeWeight] = useState(1);
  const [minDegree, setMinDegree] = useState(0);
  const [sourceGraph, setSourceGraph] = useState<GraphResult | null>(null);
  const [removedNodeIds, setRemovedNodeIds] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      setKeywordQuery(keywordInput.trim());
    }, 350);
    return () => clearTimeout(timeoutId);
  }, [keywordInput]);

  const requestParams = useMemo<NetworkParams>(
    () => ({
      query: keywordQuery || undefined,
      graph_type: graphType,
      top_n: topN,
    }),
    [keywordQuery, graphType, topN]
  );

  const fetchGraph = useCallback(async (params: NetworkParams) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getNetwork(params);
      setSourceGraph(data);
      setRemovedNodeIds([]);
      setSelectedNodeId(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load network");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchGraph(requestParams);
  }, [requestParams, fetchGraph]);

  const maxEdgeWeight = useMemo(() => {
    const graph = sourceGraph;
    if (!graph || graph.edges.length === 0) return 1;
    const highest = Math.max(...graph.edges.map((edge) => edge.weight || 1));
    return Math.max(1, Math.ceil(highest));
  }, [sourceGraph]);

  useEffect(() => {
    setMinEdgeWeight((prev) => Math.min(Math.max(1, prev), maxEdgeWeight));
  }, [maxEdgeWeight]);

  const graph = useMemo(() => {
    if (!sourceGraph) return emptyGraph(graphType);
    return applyClientFilters(
      sourceGraph,
      new Set(removedNodeIds),
      minEdgeWeight,
      minDegree
    );
  }, [sourceGraph, removedNodeIds, minEdgeWeight, minDegree, graphType]);

  useEffect(() => {
    if (selectedNodeId && !graph.nodes.some((node) => node.id === selectedNodeId)) {
      setSelectedNodeId(null);
    }
  }, [selectedNodeId, graph.nodes]);

  const handleRemoveNode = useCallback(() => {
    if (!selectedNodeId) return;
    setRemovedNodeIds((prev) =>
      prev.includes(selectedNodeId) ? prev : [...prev, selectedNodeId]
    );
    setSelectedNodeId(null);
  }, [selectedNodeId]);

  const handleResetRemoved = useCallback(() => {
    setRemovedNodeIds([]);
  }, []);

  const selectedNode: NetworkNode | null =
    graph.nodes.find((node) => node.id === selectedNodeId) ?? null;
  const topAuthor = graph.nodes[0];

  return (
    <div className="news-section">
      <SectionHeading kicker="No mischief goes unnoticed." title="The Marauder’s Network" />

      <GraphControls
        keyword={keywordInput}
        onKeywordChange={setKeywordInput}
        graphType={graphType}
        onGraphTypeChange={setGraphType}
        topN={topN}
        onTopNChange={setTopN}
        minEdgeWeight={minEdgeWeight}
        maxEdgeWeight={maxEdgeWeight}
        onMinEdgeWeightChange={setMinEdgeWeight}
        minDegree={minDegree}
        onMinDegreeChange={setMinDegree}
        selectedNode={selectedNodeId}
        onRemoveNode={handleRemoveNode}
        removedCount={removedNodeIds.length}
        onResetRemoved={handleResetRemoved}
      />

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} onRetry={() => fetchGraph(requestParams)} />
        </div>
      )}

      <div
        className="flex gap-0 overflow-hidden border-2 border-ink"
        style={{ height: "560px" }}
      >
        <div className="relative flex-[7]">
          {isLoading ? (
            <div className="absolute inset-0 flex items-center justify-center bg-wash/90">
              <div className="text-center">
                <div className="mx-auto mb-2 h-8 w-8 animate-spin rounded-full border-2 border-ink border-t-transparent" />
                <p className="byline">Loading graph...</p>
              </div>
            </div>
          ) : (
            <NetworkGraph
              nodes={graph.nodes}
              edges={graph.edges}
              graphType={graph.meta.graph_type}
              onNodeClick={setSelectedNodeId}
            />
          )}
        </div>

        <div className="flex-[3] overflow-hidden border-l border-rule bg-paper">
          <NodeSidebar node={selectedNode} onClose={() => setSelectedNodeId(null)} />
        </div>
      </div>

      <div className="mt-3 flex flex-wrap gap-6 border-t border-rule pt-3">
        <p className="data-label">{graph.nodes.length} nodes shown</p>
        <p className="data-label">{graph.edges.length} edges shown</p>
        <p className="data-label">
          Pre-limit: {graph.meta.total_nodes_before_limit} nodes /{" "}
          {graph.meta.total_edges_before_limit} edges
        </p>
        {topAuthor && <p className="data-label">Top author: {topAuthor.label}</p>}
      </div>

      {graph.meta.truncated && graph.meta.truncation_note && (
        <p className="byline mt-2">{graph.meta.truncation_note}</p>
      )}
    </div>
  );
}


