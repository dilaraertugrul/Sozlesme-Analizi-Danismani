"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  getSuggestedQuestions,
  listDocuments,
  streamChat,
  type ChatCitation,
  type DocumentSummary,
  type SuggestedQuestion,
} from "@/lib/api";
import ChatMessage, { type ChatMessageData } from "@/components/ChatMessage";
import DocumentFilter from "@/components/DocumentFilter";

function ChatPageInner() {
  const searchParams = useSearchParams();

  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [messages, setMessages] = useState<ChatMessageData[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [suggestions, setSuggestions] = useState<SuggestedQuestion[]>([]);
  const [error, setError] = useState<string | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    listDocuments().then((docs) => {
      setDocuments(docs);
      const preselect = searchParams.get("doc");
      if (preselect && docs.some((d) => d.id === preselect)) {
        setSelectedDocIds([preselect]);
      }
    });
  }, [searchParams]);

  useEffect(() => {
    if (selectedDocIds.length === 1) {
      getSuggestedQuestions(selectedDocIds[0])
        .then((res) => setSuggestions(res.questions))
        .catch(() => setSuggestions([]));
    } else {
      setSuggestions([]);
    }
  }, [selectedDocIds]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  const toggleDoc = useCallback((id: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id],
    );
  }, []);

  async function send(question: string) {
    const trimmed = question.trim();
    if (!trimmed || streaming) return;

    setError(null);
    setInput("");
    const history = messages.map((m) => ({ role: m.role, content: m.content }));
    setMessages((prev) => [
      ...prev,
      { role: "user", content: trimmed },
      { role: "assistant", content: "", streaming: true },
    ]);
    setStreaming(true);

    const controller = new AbortController();
    abortRef.current = controller;

    function updateAssistant(update: (msg: ChatMessageData) => ChatMessageData) {
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = update(next[next.length - 1]);
        return next;
      });
    }

    try {
      await streamChat(
        {
          question: trimmed,
          doc_ids: selectedDocIds.length > 0 ? selectedDocIds : null,
          history,
        },
        {
          onCitations: (citations: ChatCitation[]) =>
            updateAssistant((msg) => ({ ...msg, citations })),
          onDelta: (text: string) =>
            updateAssistant((msg) => ({ ...msg, content: msg.content + text })),
          onError: (message: string) => setError(message),
        },
        controller.signal,
      );
    } catch (err) {
      if (!(err instanceof DOMException && err.name === "AbortError")) {
        setError(err instanceof Error ? err.message : "Yanıt alınamadı.");
      }
    } finally {
      updateAssistant((msg) => ({ ...msg, streaming: false }));
      setStreaming(false);
    }
  }

  return (
    <div className="flex flex-1 justify-center bg-paper">
      <main className="flex w-full max-w-2xl flex-col px-6 py-10 lg:max-w-3xl xl:max-w-4xl">
        <div className="mb-4">
          <Link href="/" className="text-sm text-ink-3 hover:text-ink">
            ← Sözleşmeler
          </Link>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ink">Sözleşmelere soru sor</h1>
        </div>

        <DocumentFilter
          documents={documents}
          selected={selectedDocIds}
          onToggle={toggleDoc}
          onClear={() => setSelectedDocIds([])}
        />

        <div className="mt-4 flex flex-1 flex-col gap-4 overflow-y-auto py-2">
          {messages.length === 0 && (
            <p className="rounded-lg border border-dashed border-border px-4 py-8 text-center text-sm text-ink-3">
              {selectedDocIds.length === 0
                ? "Tüm sözleşmeler kapsamında bir soru sorabilirsiniz. Örnek sorular için üstten tek bir sözleşme seçin."
                : "Seçili sözleşme(ler) hakkında bir soru sorabilirsiniz."}
            </p>
          )}
          {messages.map((message, i) => (
            <ChatMessage key={i} message={message} />
          ))}
          <div ref={bottomRef} />
        </div>

        {error && (
          <p
            className="mb-2 rounded-lg px-4 py-2 text-sm"
            style={{ backgroundColor: "var(--status-critical-bg)", color: "var(--status-critical)" }}
          >
            {error}
          </p>
        )}

        {suggestions.length > 0 && messages.length === 0 && (
          <div className="mb-3 flex flex-wrap gap-2">
            {suggestions.map((s, i) => (
              <button
                key={i}
                onClick={() => send(s.question)}
                className="rounded-full border border-border px-3 py-1.5 text-left text-xs text-ink-2 hover:border-accent/50 hover:text-ink"
              >
                {s.question}
              </button>
            ))}
          </div>
        )}

        <form
          onSubmit={(e) => {
            e.preventDefault();
            void send(input);
          }}
          className="flex items-end gap-2"
        >
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void send(input);
              }
            }}
            placeholder="Örn. Fesih koşulları nedir?"
            rows={1}
            className="max-h-32 flex-1 resize-none rounded-lg border border-border bg-surface px-3 py-2.5 text-sm text-ink outline-none placeholder:text-ink-3 focus:border-accent"
          />
          <button
            type="submit"
            disabled={streaming || !input.trim()}
            className="rounded-lg bg-accent px-4 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-accent-hover hover:shadow-md disabled:opacity-40 disabled:shadow-none"
          >
            Gönder
          </button>
        </form>
      </main>
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense>
      <ChatPageInner />
    </Suspense>
  );
}
