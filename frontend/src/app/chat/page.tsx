"use client";

import { useState, useRef, useCallback } from "react";
import { streamChat } from "@/lib/api";
import { ChatMessage, SearchResult } from "@/types";
import ChatWindow from "@/components/chat/ChatWindow";
import ChatInput from "@/components/chat/ChatInput";
import SourcePanel from "@/components/chat/SourcePanel";
import SuggestedQueries from "@/components/chat/SuggestedQueries";
import SectionHeading from "@/components/ui/SectionHeading";

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streamingContent, setStreamingContent] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sources, setSources] = useState<SearchResult[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const abortRef = useRef<AbortController | null>(null);

  const handleSubmit = useCallback(
    (query: string) => {
      if (!query.trim() || isStreaming) return;

      // Abort any previous stream
      abortRef.current?.abort();

      const userMsg: ChatMessage = { role: "user", content: query };
      setMessages((prev) => [...prev, userMsg]);
      setStreamingContent("");
      setIsStreaming(true);
      setError(null);
      setSuggestions([]);
      setSources([]);

      let accumulated = "";

      const ctrl = streamChat(
        { query, messages },
        (token) => {
          accumulated += token;
          setStreamingContent(accumulated);
        },
        (retrievedSources) => {
          setSources(retrievedSources);
        },
        (suggested) => {
          setSuggestions(suggested);
        },
        (err) => {
          setError(err);
          setIsStreaming(false);
        },
        () => {
          const assistantMsg: ChatMessage = { role: "assistant", content: accumulated };
          setMessages((prev) => [...prev, assistantMsg]);
          setStreamingContent("");
          setIsStreaming(false);
        }
      );

      abortRef.current = ctrl;
    },
    [isStreaming, messages]
  );

  return (
    <div>
      <SectionHeading kicker="RAG Intelligence" title="Ask the Dataset" />
      <p className="byline mb-6">
        Semantic retrieval + Gemini 1.5 Flash · Multilingual · Sources shown →
      </p>

      <div
        className="border border-rule rounded overflow-hidden flex"
        style={{ height: "calc(100vh - 300px)", minHeight: "500px" }}
      >
        {/* Chat — 60% */}
        <div className="flex-[3] flex flex-col min-h-0">
          <ChatWindow
            messages={messages}
            isStreaming={isStreaming}
            streamingContent={streamingContent}
            error={error}
            onRetry={() => {
              const lastUser = [...messages].reverse().find((m) => m.role === "user");
              if (lastUser) handleSubmit(lastUser.content);
            }}
          />
          {suggestions.length > 0 && (
            <SuggestedQueries suggestions={suggestions} onSelect={handleSubmit} />
          )}
          <ChatInput onSubmit={handleSubmit} isStreaming={isStreaming} />
        </div>

        {/* Sources — 40% */}
        <div className="flex-[2] min-h-0 overflow-hidden">
          <SourcePanel sources={sources} isLoading={isStreaming && sources.length === 0} />
        </div>
      </div>
    </div>
  );
}
