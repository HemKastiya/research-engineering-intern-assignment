"use client";

import { useEffect, useRef } from "react";
import { ChatMessage } from "@/types";
import MessageBubble from "./MessageBubble";

interface ChatWindowProps {
  messages: ChatMessage[];
  isStreaming?: boolean;
  streamingContent?: string;
  error?: string | null;
  onRetry?: () => void;
}

export default function ChatWindow({
  messages,
  isStreaming,
  streamingContent,
  error,
  onRetry,
}: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  return (
    <div className="flex-1 min-h-0 space-y-2 overflow-y-auto p-4">
      {messages.length === 0 && !isStreaming && (
        <div className="flex h-full flex-col items-center justify-center py-12 text-center">
          <div className="mb-4 w-12 border-t-2 border-ink" />
          <p className="kicker mb-2">Intelligence Wire</p>
          <p className="section-head mb-2">Ask the dataset anything</p>
          <p className="deck-text text-sm">
            Responses are grounded in semantic retrieval and the posts currently indexed in your corpus.
          </p>
        </div>
      )}

      {messages.map((msg, i) => (
        <MessageBubble
          key={i}
          message={msg}
          isStreaming={isStreaming && i === messages.length - 1 && msg.role === "assistant"}
        />
      ))}

      {isStreaming && streamingContent && (
        <MessageBubble message={{ role: "assistant", content: streamingContent }} isStreaming />
      )}

      {error && (
        <div className="flex items-center justify-between gap-3 border border-accent px-4 py-3 text-xs" style={{ backgroundColor: "var(--color-accent-soft)" }}>
          <p className="text-muted">{error}</p>
          {onRetry && (
            <button onClick={onRetry} className="press-btn press-btn-ghost border-accent text-xs text-accent">
              Retry
            </button>
          )}
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
