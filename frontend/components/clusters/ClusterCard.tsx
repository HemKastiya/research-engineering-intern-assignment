import { ClusterTopic } from "@/types";
import Badge from "@/components/ui/Badge";

interface ClusterCardProps {
  topic: ClusterTopic;
  maxCount: number;
  isActive?: boolean;
  onClick?: () => void;
}

export default function ClusterCard({ topic, maxCount, isActive, onClick }: ClusterCardProps) {
  const barWidth = maxCount > 0 ? (topic.count / maxCount) * 100 : 0;

  return (
    <button
      onClick={onClick}
      className={[
        "w-full text-left press-card transition-all",
        isActive ? "border-accent shadow-sm" : "",
      ].join(" ")}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <span className="kicker">Cluster {topic.topic_id}</span>
        <span className="data-label">{topic.count} posts</span>
      </div>

      {/* Top terms */}
      <div className="flex flex-wrap gap-1 mb-3">
        {(topic.representation ?? []).slice(0, 5).map((term) => (
          <Badge key={term} variant={isActive ? "accent" : "default"}>
            {term}
          </Badge>
        ))}
      </div>

      {/* Size bar */}
      <div className="w-full h-1 bg-rule rounded-full overflow-hidden">
        <div
          className="h-full bg-accent transition-all duration-300"
          style={{ width: `${barWidth}%` }}
        />
      </div>
    </button>
  );
}
