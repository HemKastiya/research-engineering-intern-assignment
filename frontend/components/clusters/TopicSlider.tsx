interface TopicSliderProps {
  value: number;
  onChange: (n: number) => void;
  isLoading?: boolean;
}

export default function TopicSlider({ value, onChange, isLoading }: TopicSliderProps) {
  return (
    <div className="flex items-center gap-4 border border-rule bg-wash p-4">
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
      <span className="w-10 text-center font-playfair text-2xl font-black leading-none text-ink">{value}</span>
      {isLoading && <span className="data-label animate-pulse">Clustering...</span>}
    </div>
  );
}
