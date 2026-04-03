"use client";

import { useEffect, useRef } from "react";
import { ChatMessage } from "@/types";
import MessageBubble from "./MessageBubble";
import LoadingSkeleton from "@/components/ui/LoadingSkeleton";

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
    <div className="flex-1 overflow-y-auto p-4 space-y-2 min-h-0">
      {messages.length === 0 && !isStreaming && (
        <div className="flex flex-col items-center justify-center h-full text-center py-12">
          <div className="w-12 border-t-2 border-ink mb-4" />
          <p className="kicker mb-2">Intelligence</p>
          <p className="section-head mb-2">Ask the dataset anything</p>
          <p className="byline max-w-sm">
            Uses semantic search + RAG to answer questions grounded in your Reddit data.
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
        <MessageBubble
          message={{ role: "assistant", content: streamingContent }}
          isStreaming
        />
      )}

      {error && (
        <div className="border-l-2 border-accent bg-[#fef2f2] px-4 py-3 flex items-center justify-between text-xs gap-3">
          <p className="text-muted">{error}</p>
          {onRetry && (
            <button onClick={onRetry} className="press-btn press-btn-ghost text-xs border-accent text-accent">
              Retry
            </button>
          )}
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
