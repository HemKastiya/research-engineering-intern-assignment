interface TopicSliderProps {
  value: number;
  onChange: (n: number) => void;
  isLoading?: boolean;
}

export default function TopicSlider({ value, onChange, isLoading }: TopicSliderProps) {
  return (
    <div className="flex items-center gap-4 p-4 bg-wash border border-rule rounded">
      <label className="kicker whitespace-nowrap">Target topics</label>
      <input
        type="range"
        min={2}
        max={50}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="flex-1 accent-accent"
        disabled={isLoading}
      />
      <span className="font-playfair text-2xl font-black text-ink w-10 text-center leading-none">
        {value}
      </span>
      {isLoading && (
        <span className="data-label animate-pulse">Clustering…</span>
      )}
    </div>
  );
}
