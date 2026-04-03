import { NetworkNode } from "@/types";
import { formatScore } from "@/lib/utils";

interface NodeSidebarProps {
  node: NetworkNode | null;
  onClose: () => void;
}

export default function NodeSidebar({ node, onClose }: NodeSidebarProps) {
  if (!node) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-center p-8">
        <div className="w-8 border-t border-rule mb-4" />
        <p className="kicker mb-2">Author Detail</p>
        <p className="byline">Click a node in the graph to view author details</p>
      </div>
    );
  }

  return (
    <div className="p-6 h-full overflow-y-auto">
      <div className="flex items-center justify-between mb-4">
        <p className="kicker">Author Profile</p>
        <button onClick={onClose} className="text-muted hover:text-ink text-lg leading-none">×</button>
      </div>
      <div className="border-t border-rule mb-4" />

      <h3 className="section-head mb-1">{node.label}</h3>
      <p className="byline mb-6">u/{node.id}</p>

      <div className="space-y-4">
        <div className="press-card">
          <p className="kicker mb-1">PageRank Score</p>
          <p className="font-playfair text-2xl font-black text-ink">
            {node.pagerank_score?.toFixed(6) ?? "—"}
          </p>
        </div>
        <div className="press-card">
          <p className="kicker mb-1">Community</p>
          <p className="font-playfair text-2xl font-black text-ink">
            #{node.community_id ?? "—"}
          </p>
        </div>
      </div>
    </div>
  );
}
