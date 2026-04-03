import { ChatMessage } from "@/types";

interface MessageBubbleProps {
  message: ChatMessage;
  isStreaming?: boolean;
}

export default function MessageBubble({ message, isStreaming }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div
        className={[
          "max-w-[80%] rounded px-4 py-3 text-sm leading-relaxed",
          isUser
            ? "bg-ink text-paper"
            : "bg-white border border-rule text-ink",
        ].join(" ")}
      >
        {!isUser && (
          <p className="kicker mb-2">AI Assistant</p>
        )}
        <p className={isStreaming && !isUser ? "blink-cursor" : ""}>
          {message.content}
        </p>
      </div>
    </div>
  );
}
