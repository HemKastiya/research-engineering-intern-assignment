interface GraphControlsProps {
  subreddit: string;
  onSubredditChange: (v: string) => void;
  minEdgeWeight: number;
  onMinEdgeWeightChange: (v: number) => void;
  selectedNode: string | null;
  onRemoveNode: () => void;
  isRemoving?: boolean;
}

export default function GraphControls({
  subreddit,
  onSubredditChange,
  minEdgeWeight,
  onMinEdgeWeightChange,
  selectedNode,
  onRemoveNode,
  isRemoving,
}: GraphControlsProps) {
  return (
    <div className="flex flex-wrap items-center gap-4 mb-4 p-4 bg-wash border border-rule rounded">
      <div className="flex items-center gap-2">
        <label className="kicker whitespace-nowrap">Subreddit filter</label>
        <input
          className="press-input w-36"
          placeholder="e.g. science"
          value={subreddit}
          onChange={(e) => onSubredditChange(e.target.value)}
        />
      </div>

      <div className="flex items-center gap-2">
        <label className="kicker whitespace-nowrap">Min edge weight</label>
        <input
          type="range"
          min={1}
          max={10}
          value={minEdgeWeight}
          onChange={(e) => onMinEdgeWeightChange(Number(e.target.value))}
          className="w-24 accent-accent"
        />
        <span className="data-label w-4">{minEdgeWeight}</span>
      </div>

      {selectedNode && (
        <button
          onClick={onRemoveNode}
          disabled={isRemoving}
          className="press-btn ml-auto text-xs"
        >
          {isRemoving ? "Removing…" : `Remove "${selectedNode}"`}
        </button>
      )}
    </div>
  );
}
