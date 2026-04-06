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
    <div className="news-section">
      <SectionHeading kicker="Consult the wisdom hidden within the dataset." title="Ask the Oracle" />
      <p className="byline mb-6">
        Semantic retrieval + Gemini 2.5 Flash | Multilingual support | Sources included
      </p>

      <div className="flex overflow-hidden border-2 border-ink bg-paper" style={{ height: "calc(100vh - 300px)", minHeight: "500px" }}>
        <div className="flex min-h-0 flex-[3] flex-col border-r border-rule">
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
          {suggestions.length > 0 && <SuggestedQueries suggestions={suggestions} onSelect={handleSubmit} />}
          <ChatInput onSubmit={handleSubmit} isStreaming={isStreaming} />
        </div>

        <div className="min-h-0 flex-[2] overflow-hidden bg-wash/40">
          <SourcePanel sources={sources} isLoading={isStreaming && sources.length === 0} />
        </div>
      </div>
    </div>
  );
}
