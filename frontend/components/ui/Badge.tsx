import { cn } from "@/lib/utils";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "accent";
  className?: string;
}

export default function Badge({ children, variant = "default", className }: BadgeProps) {
  return (
    <span
      className={cn(
        "pill-badge",
        variant === "accent" && "pill-badge-accent",
        className
      )}
    >
      {children}
    </span>
  );
}
