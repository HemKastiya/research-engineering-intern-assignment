"use client";

import { useState, useEffect, useCallback } from "react";
import { getNetwork, deleteNetworkNode, NetworkParams } from "@/lib/api";
import { NetworkNode, NetworkEdge, GraphResult } from "@/types";
import dynamic from "next/dynamic";
import GraphControls from "@/components/network/GraphControls";
import NodeSidebar from "@/components/network/NodeSidebar";
import SectionHeading from "@/components/ui/SectionHeading";
import ErrorBanner from "@/components/ui/ErrorBanner";
import LoadingSkeleton from "@/components/ui/LoadingSkeleton";

// Sigma uses canvas; must be client-only
const NetworkGraph = dynamic(
  () => import("@/components/network/NetworkGraph"),
  { ssr: false, loading: () => <LoadingSkeleton variant="chart" /> }
);

export default function NetworkPage() {
  const [subreddit, setSubreddit] = useState("");
  const [minEdgeWeight, setMinEdgeWeight] = useState(1);
  const [graph, setGraph] = useState<GraphResult>({ nodes: [], edges: [] });
  const [isLoading, setIsLoading] = useState(true);
  const [isRemoving, setIsRemoving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [debouncedParams, setDebouncedParams] = useState<NetworkParams>({ min_edge_weight: 1 });

  useEffect(() => {
    const id = setTimeout(() => {
      setDebouncedParams({
        subreddit: subreddit || undefined,
        min_edge_weight: minEdgeWeight,
      });
    }, 500);
    return () => clearTimeout(id);
  }, [subreddit, minEdgeWeight]);

  const fetchGraph = useCallback(async (params: NetworkParams) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getNetwork(params);
      setGraph(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load network");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchGraph(debouncedParams);
  }, [debouncedParams, fetchGraph]);

  const handleRemoveNode = async () => {
    if (!selectedNodeId) return;
    setIsRemoving(true);
    try {
      // Optimistic update
      const prev = graph;
      setGraph({
        nodes: graph.nodes.filter((n) => n.id !== selectedNodeId),
        edges: graph.edges.filter(
          (e) => e.source !== selectedNodeId && e.target !== selectedNodeId
        ),
      });
      setSelectedNodeId(null);
      const updated = await deleteNetworkNode(selectedNodeId, debouncedParams);
      setGraph(updated);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to remove node");
      // Rollback by refetching
      fetchGraph(debouncedParams);
    } finally {
      setIsRemoving(false);
    }
  };

  const selectedNode = graph.nodes.find((n) => n.id === selectedNodeId) ?? null;

  return (
    <div>
      <SectionHeading kicker="Graph Analysis" title="Author Interaction Network" />

      <GraphControls
        subreddit={subreddit}
        onSubredditChange={setSubreddit}
        minEdgeWeight={minEdgeWeight}
        onMinEdgeWeightChange={setMinEdgeWeight}
        selectedNode={selectedNodeId}
        onRemoveNode={handleRemoveNode}
        isRemoving={isRemoving}
      />

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} onRetry={() => fetchGraph(debouncedParams)} />
        </div>
      )}

      <div className="flex gap-0 border border-rule rounded overflow-hidden" style={{ height: "560px" }}>
        {/* Graph canvas — 70% */}
        <div className="flex-[7] relative">
          {isLoading ? (
            <div className="absolute inset-0 flex items-center justify-center bg-wash">
              <div className="text-center">
                <div className="w-8 h-8 border-2 border-ink border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                <p className="byline">Loading graph…</p>
              </div>
            </div>
          ) : (
            <NetworkGraph
              nodes={graph.nodes}
              edges={graph.edges}
              onNodeClick={setSelectedNodeId}
            />
          )}
        </div>

        {/* Sidebar — 30% */}
        <div className="flex-[3] border-l border-rule bg-paper overflow-hidden">
          <NodeSidebar node={selectedNode} onClose={() => setSelectedNodeId(null)} />
        </div>
      </div>

      <div className="mt-3 flex gap-6">
        <p className="data-label">{graph.nodes.length} nodes</p>
        <p className="data-label">{graph.edges.length} edges</p>
        {graph.nodes.length > 0 && (
          <p className="data-label">
            Top author: {graph.nodes.sort((a, b) => (b.pagerank_score ?? 0) - (a.pagerank_score ?? 0))[0]?.label}
          </p>
        )}
      </div>
    </div>
  );
}
