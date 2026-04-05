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
    <nav className="sticky top-0 z-30 overflow-x-auto border-y border-rule bg-paper/95 backdrop-blur-[1px]">
      <div className="flex min-w-max items-center gap-1 px-6">
        <span className="dateline mr-1 border-r border-rule pr-2">Sections</span>
        {TABS.map((tab, i) => {
          const isActive = tab.href === "/" ? pathname === "/" : pathname.startsWith(tab.href);

          return (
            <div key={tab.href} className="flex items-center">
              <Link
                href={tab.href}
                className={[
                  "whitespace-nowrap border-b-2 px-3 py-3 text-[0.68rem] font-semibold uppercase tracking-[0.17em] transition-colors",
                  isActive
                    ? "border-accent text-accent"
                    : "border-transparent text-muted hover:border-rule hover:text-ink",
                ].join(" ")}
              >
                {tab.label}
              </Link>
              {i < TABS.length - 1 && <span className="mx-0.5 text-rule">|</span>}
            </div>
          );
        })}
      </div>
    </nav>
  );
}
