import { ClusterTopic } from "@/types";
import ClusterCard from "./ClusterCard";
import LoadingSkeleton from "@/components/ui/LoadingSkeleton";
import EmptyState from "@/components/ui/EmptyState";

interface ClusterPanelProps {
  topics: ClusterTopic[];
  isLoading?: boolean;
  activeCluster?: number | null;
  onClusterClick?: (id: number) => void;
}

export default function ClusterPanel({ topics, isLoading, activeCluster, onClusterClick }: ClusterPanelProps) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <LoadingSkeleton key={i} variant="card" lines={2} />
        ))}
      </div>
    );
  }

  if (!topics || topics.length === 0) {
    return (
      <EmptyState
        title="No topics found"
        description="Try adjusting the number of topics with the slider above."
      />
    );
  }

  const maxCount = Math.max(...topics.map((t) => t.count));

  return (
    <div className="space-y-2 overflow-y-auto max-h-[600px] pr-1">
      {topics.map((topic) => (
        <ClusterCard
          key={topic.topic_id}
          topic={topic}
          maxCount={maxCount}
          isActive={activeCluster === topic.topic_id}
          onClick={() => onClusterClick?.(topic.topic_id)}
        />
      ))}
    </div>
  );
}
