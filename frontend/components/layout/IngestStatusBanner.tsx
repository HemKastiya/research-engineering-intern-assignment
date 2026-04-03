"use client";

import { useEffect, useState } from "react";
import { getIngestStatus } from "@/lib/api";
import { IngestStatus } from "@/types";

export default function IngestStatusBanner() {
  const [status, setStatus] = useState<IngestStatus | null>(null);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const poll = async () => {
      if (cancelled) return;
      try {
        const data = await getIngestStatus();
        if (cancelled) return;
        setStatus(data);

        // Poll only while processing; stop when terminal state is reached.
        if (data.embedding_status === "Processing") {
          timer = setTimeout(poll, 8000);
        }
      } catch {
        if (!cancelled) {
          // Back off a bit on transient failures.
          timer = setTimeout(poll, 15000);
        }
      }
    };

    poll();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, []);

  if (!status || status.embedding_status === "Idle") return null;

  return (
    <div className="bg-ink text-paper px-6 py-2 flex items-center justify-between text-xs font-inter">
      <div className="flex items-center gap-2">
        <span className="inline-block w-2 h-2 rounded-full bg-accent animate-pulse" />
        <span className="font-medium uppercase tracking-wider">
          Indexing in progress
        </span>
        <span className="text-rule">
          — {status.mongo_documents.toLocaleString()} posts ·{" "}
          {status.chroma_vectors.toLocaleString()} vectors indexed
        </span>
      </div>
      <span className="data-label text-rule">{status.embedding_status}</span>
    </div>
  );
}
