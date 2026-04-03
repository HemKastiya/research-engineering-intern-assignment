import { NetworkGraphType } from "@/types";

const GRAPH_TYPE_OPTIONS: Array<{ value: NetworkGraphType; label: string }> = [
  { value: "co_subreddit", label: "Co-Subreddit" },
  { value: "crosspost", label: "Crosspost" },
  { value: "shared_domain", label: "Shared Domain" },
];

const TOP_N_OPTIONS = [100, 150, 200, 250];

interface GraphControlsProps {
  keyword: string;
  onKeywordChange: (v: string) => void;
  graphType: NetworkGraphType;
  onGraphTypeChange: (v: NetworkGraphType) => void;
  topN: number;
  onTopNChange: (v: number) => void;
  minEdgeWeight: number;
  maxEdgeWeight: number;
  onMinEdgeWeightChange: (v: number) => void;
  minDegree: number;
  onMinDegreeChange: (v: number) => void;
  selectedNode: string | null;
  onRemoveNode: () => void;
  removedCount: number;
  onResetRemoved: () => void;
}

export default function GraphControls({
  keyword,
  onKeywordChange,
  graphType,
  onGraphTypeChange,
  topN,
  onTopNChange,
  minEdgeWeight,
  maxEdgeWeight,
  onMinEdgeWeightChange,
  minDegree,
  onMinDegreeChange,
  selectedNode,
  onRemoveNode,
  removedCount,
  onResetRemoved,
}: GraphControlsProps) {
  return (
    <div className="mb-4 rounded border border-rule bg-wash p-4">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        {GRAPH_TYPE_OPTIONS.map((option) => (
          <button
            key={option.value}
            onClick={() => onGraphTypeChange(option.value)}
            className={`pill-badge cursor-pointer transition-colors ${
              graphType === option.value ? "pill-badge-accent border-accent" : ""
            }`}
          >
            {option.label}
          </button>
        ))}
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <div className="flex items-center gap-2">
          <label className="kicker whitespace-nowrap">Keyword</label>
          <input
            className="press-input w-full"
            placeholder="e.g. climate policy"
            value={keyword}
            onChange={(e) => onKeywordChange(e.target.value)}
          />
        </div>

        <div className="flex items-center gap-2">
          <label className="kicker whitespace-nowrap">Top N</label>
          <select
            className="press-input w-full py-2"
            value={topN}
            onChange={(e) => onTopNChange(Number(e.target.value))}
          >
            {TOP_N_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option} authors
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label className="kicker whitespace-nowrap">Min edge</label>
          <input
            type="range"
            min={1}
            max={Math.max(1, maxEdgeWeight)}
            value={Math.min(minEdgeWeight, Math.max(1, maxEdgeWeight))}
            onChange={(e) => onMinEdgeWeightChange(Number(e.target.value))}
            className="w-full accent-accent"
          />
          <span className="data-label min-w-8 text-right">{minEdgeWeight}</span>
        </div>

        <div className="flex items-center gap-2">
          <label className="kicker whitespace-nowrap">Min degree</label>
          <input
            type="range"
            min={0}
            max={10}
            value={minDegree}
            onChange={(e) => onMinDegreeChange(Number(e.target.value))}
            className="w-full accent-accent"
          />
          <span className="data-label min-w-8 text-right">{minDegree}</span>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        {selectedNode && (
          <button onClick={onRemoveNode} className="press-btn text-xs">
            Remove {selectedNode}
          </button>
        )}
        <button
          onClick={onResetRemoved}
          disabled={removedCount === 0}
          className="press-btn press-btn-ghost text-xs disabled:cursor-not-allowed disabled:opacity-50"
        >
          Restore removed ({removedCount})
        </button>
      </div>
    </div>
  );
}
