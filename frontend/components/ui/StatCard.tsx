interface StatCardProps {
  label: string;
  value: string | number | null | undefined;
  sub?: string;
}

export default function StatCard({ label, value, sub }: StatCardProps) {
  const display =
    value == null
      ? "—"
      : typeof value === "number"
      ? value.toLocaleString()
      : value;

  return (
    <div className="press-card text-center">
      <p className="kicker mb-1">{label}</p>
      <p className="font-playfair text-3xl font-black text-ink leading-none mb-1">
        {display}
      </p>
      {sub && <p className="byline">{sub}</p>}
    </div>
  );
}
