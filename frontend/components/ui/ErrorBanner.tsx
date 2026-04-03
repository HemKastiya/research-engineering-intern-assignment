interface ErrorBannerProps {
  message: string;
  onRetry?: () => void;
}

export default function ErrorBanner({ message, onRetry }: ErrorBannerProps) {
  return (
    <div className="border-l-2 border-accent bg-[#fef2f2] px-4 py-3 flex items-start justify-between gap-4 rounded-r">
      <div>
        <p className="kicker mb-1">Error</p>
        <p className="body-text text-muted">{message}</p>
      </div>
      {onRetry && (
        <button onClick={onRetry} className="press-btn press-btn-ghost text-accent border-accent hover:bg-[#fef2f2] shrink-0">
          Try again
        </button>
      )}
    </div>
  );
}
