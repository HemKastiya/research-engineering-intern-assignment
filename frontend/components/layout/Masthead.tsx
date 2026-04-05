import { mastheadTokens } from "@/lib/tokens";

interface MastheadProps {
  totalRecords?: number | null;
  dateRange?: string;
}

export default function Masthead({ totalRecords, dateRange }: MastheadProps) {
  const today = new Date().toLocaleDateString("en-GB", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <header className="border-b-2 border-ink bg-paper px-6 pt-4 pb-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <span className="dateline">Vol. I | No. 1</span>
        <span className="dateline">{today}</span>
      </div>

      <div className="mb-3 border-t border-rule" />

      <div className="px-2 text-center">
        <p className="kicker mb-1 text-ink">Data Intelligence Desk</p>
        <h1 className="masthead-text tracking-tight">{mastheadTokens.name}</h1>
        <p className="byline mt-1 text-[0.64rem] uppercase tracking-[0.24em]">
          {mastheadTokens.tagline}
        </p>
      </div>

      <div className="mt-3 border-t border-ink" />
      <div className="mt-1 flex flex-wrap items-center justify-between gap-2">
        <span className="dateline">Published daily from live corpus signals</span>
        <div className="flex flex-wrap items-center gap-4">
          {dateRange && <span className="data-label">Data window: {dateRange}</span>}
          {totalRecords != null && (
            <span className="data-label">{totalRecords.toLocaleString()} records indexed</span>
          )}
        </div>
      </div>
    </header>
  );
}
