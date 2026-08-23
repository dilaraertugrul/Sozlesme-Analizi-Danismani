import type { ChatCitation } from "@/lib/api";

export type ChatMessageData = {
  role: "user" | "assistant";
  content: string;
  citations?: ChatCitation[];
  streaming?: boolean;
};

export default function ChatMessage({ message }: { message: ChatMessageData }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[85%] ${isUser ? "" : "w-full"}`}>
        <div
          className={`whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
            isUser ? "bg-accent text-white" : "bg-surface text-ink border border-border"
          }`}
        >
          {message.content || (message.streaming ? "…" : "")}
        </div>

        {!isUser && message.citations && message.citations.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {message.citations.map((c, i) => (
              <span
                key={c.chunk_id}
                title={c.excerpt}
                className="inline-flex items-center gap-1 rounded-md bg-accent-soft px-2 py-1 text-xs text-ink-2"
              >
                <span className="font-medium text-accent">K{i + 1}</span>
                {c.label}
                {c.doc_title ? ` · ${c.doc_title}` : ""}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
