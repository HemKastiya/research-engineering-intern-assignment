import { ChatMessage } from "@/types";

interface MessageBubbleProps {
  message: ChatMessage;
  isStreaming?: boolean;
}

export default function MessageBubble({ message, isStreaming }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`mb-4 flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={[
          "max-w-[80%] border px-4 py-3 text-sm leading-relaxed",
          isUser
            ? "border-ink bg-ink text-paper"
            : "border-rule bg-white text-ink",
        ].join(" ")}
      >
        {!isUser && <p className="kicker mb-2">AI Desk</p>}
        <p className={isStreaming && !isUser ? "blink-cursor" : ""}>{message.content}</p>
      </div>
    </div>
  );
}
