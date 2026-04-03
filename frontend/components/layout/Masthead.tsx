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
    <header className="border-b-2 border-ink bg-paper px-6 py-4">
      {/* Top rule with edition info */}
      <div className="flex items-center justify-between mb-2">
        <span className="data-label">Vol. I — No. 1</span>
        <div className="flex items-center gap-4">
          {dateRange && (
            <span className="data-label">Data: {dateRange}</span>
          )}
          {totalRecords != null && (
            <span className="data-label">{totalRecords.toLocaleString()} records indexed</span>
          )}
          <span className="data-label">{today}</span>
        </div>
      </div>

      {/* Hairline rule */}
      <div className="border-t border-rule mb-3" />

      {/* Masthead name */}
      <div className="text-center">
        <h1 className="masthead-text tracking-tight">{mastheadTokens.name}</h1>
        <p className="byline mt-1 tracking-widest uppercase text-[0.65rem]">
          {mastheadTokens.tagline}
        </p>
      </div>

      {/* Bottom rule */}
      <div className="border-t-2 border-ink mt-3" />
    </header>
  );
}
