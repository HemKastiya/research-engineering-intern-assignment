interface LoadingSkeletonProps {
  lines?: number;
  variant?: "card" | "chart" | "table" | "text";
}

export default function LoadingSkeleton({
  lines = 3,
  variant = "card",
}: LoadingSkeletonProps) {
  if (variant === "chart") {
    return <div className="skeleton w-full h-64" />;
  }

  if (variant === "table") {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="skeleton h-10 w-full" />
        ))}
      </div>
    );
  }

  if (variant === "card") {
    return (
      <div className="press-card space-y-3">
        <div className="skeleton h-3 w-16" />
        <div className="skeleton h-5 w-3/4" />
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className="skeleton h-3"
            style={{ width: `${85 - i * 10}%` }}
          />
        ))}
        <div className="skeleton h-3 w-20 mt-4" />
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="skeleton h-3"
          style={{ width: `${90 - i * 8}%` }}
        />
      ))}
    </div>
  );
}
