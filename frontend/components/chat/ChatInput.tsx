"use client";

import { useState, KeyboardEvent } from "react";

interface ChatInputProps {
  onSubmit: (query: string) => void;
  isStreaming?: boolean;
}

export default function ChatInput({ onSubmit, isStreaming }: ChatInputProps) {
  const [value, setValue] = useState("");

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (!trimmed || isStreaming) return;
    onSubmit(trimmed);
    setValue("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="border-t border-rule bg-paper p-4">
      <div className="flex items-end gap-2">
        <textarea
          id="chat-input"
          className="press-input flex-1 resize-none"
          rows={2}
          placeholder="Ask a question about the dataset... (Enter to send, Shift+Enter for newline)"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isStreaming}
        />
        <button
          onClick={handleSubmit}
          disabled={!value.trim() || isStreaming}
          className="press-btn h-[58px] shrink-0"
        >
          {isStreaming ? "..." : "Send"}
        </button>
      </div>
      <p className="byline mt-1">Multilingual queries supported | Shift+Enter for newline</p>
    </div>
  );
}
