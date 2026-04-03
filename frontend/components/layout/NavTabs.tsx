"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/", label: "Overview" },
  { href: "/timeseries", label: "Time Series" },
  { href: "/search", label: "Search" },
  { href: "/network", label: "Network" },
  { href: "/clusters", label: "Clusters" },
  { href: "/embeddings", label: "Embeddings" },
  { href: "/chat", label: "Intelligence" },
];

export default function NavTabs() {
  const pathname = usePathname();

  return (
    <nav className="sticky top-0 z-30 bg-paper border-b border-rule overflow-x-auto">
      <div className="flex items-center px-6 min-w-max">
        {TABS.map((tab, i) => {
          const isActive = tab.href === "/"
            ? pathname === "/"
            : pathname.startsWith(tab.href);

          return (
            <div key={tab.href} className="flex items-center">
              {i > 0 && (
                <span className="text-rule mx-1 select-none">·</span>
              )}
              <Link
                href={tab.href}
                className={[
                  "px-3 py-3 text-xs font-semibold uppercase tracking-widest transition-colors whitespace-nowrap",
                  "border-b-2",
                  isActive
                    ? "border-accent text-accent"
                    : "border-transparent text-muted hover:text-ink hover:border-rule",
                ].join(" ")}
              >
                {tab.label}
              </Link>
            </div>
          );
        })}
      </div>
    </nav>
  );
}
