import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(iso: string): string {
  if (!iso) return '';
  const date = new Date(iso);
  const formatter = new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  });
  return formatter.format(date); // e.g., "18 Feb 2025"
}

export function truncate(text: string | null | undefined, maxLen: number): string {
  if (!text) return '';
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen).trim() + '...';
}

export function formatScore(n: number | null | undefined): string {
  if (n == null) return "0";
  return n.toLocaleString();
}

export function clampPageRank(pr: number | null | undefined, min: number = 4, max: number = 40): number {
  if (pr == null) return min;
  // A heuristic mapping: assuming pagerank_score ranges roughly 0..1
  // Scale appropriately depending on real range. Let's assume a factor of 100 for now.
  const scaled = pr * 50; 
  if (scaled < min) return min;
  if (scaled > max) return max;
  return scaled;
}
