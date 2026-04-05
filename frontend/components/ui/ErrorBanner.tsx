interface ErrorBannerProps {
  message: string;
  onRetry?: () => void;
}

export default function ErrorBanner({ message, onRetry }: ErrorBannerProps) {
  return (
    <div
      className="flex items-start justify-between gap-4 border border-accent px-4 py-3"
      style={{ backgroundColor: "var(--color-accent-soft)" }}
    >
      <div>
        <p className="kicker mb-1">Error Desk</p>
        <p className="body-text text-sm text-ink-soft">{message}</p>
      </div>
      {onRetry && (
        <button onClick={onRetry} className="press-btn press-btn-ghost shrink-0 border-accent text-accent">
          Try again
        </button>
      )}
    </div>
  );
}
