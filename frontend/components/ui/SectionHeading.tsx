interface SectionHeadingProps {
  kicker?: string;
  title: string;
  className?: string;
}

export default function SectionHeading({ kicker, title, className = "" }: SectionHeadingProps) {
  return (
    <div className={`mb-5 ${className}`}>
      {kicker && <p className="kicker mb-1">{kicker}</p>}
      <h2 className="section-head">{title}</h2>
      <div className="section-heading-rule" />
    </div>
  );
}
