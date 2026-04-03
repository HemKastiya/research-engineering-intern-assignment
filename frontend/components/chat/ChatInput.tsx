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
    <div className="border-t border-rule p-4 bg-paper">
      <div className="flex gap-2 items-end">
        <textarea
          id="chat-input"
          className="press-input resize-none flex-1"
          rows={2}
          placeholder="Ask a question about the dataset… (Enter to send, Shift+Enter for newline)"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isStreaming}
        />
        <button
          onClick={handleSubmit}
          disabled={!value.trim() || isStreaming}
          className="press-btn shrink-0 h-[58px]"
        >
          {isStreaming ? "…" : "Send"}
        </button>
      </div>
      <p className="byline mt-1">Multilingual queries supported · Shift+Enter for newline</p>
    </div>
  );
}
