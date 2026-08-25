"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  listDocuments,
  streamCompare,
  type CompareResult,
  type CompareTopic,
  type DocumentSummary,
} from "@/lib/api";
import DocumentPicker from "@/components/DocumentPicker";
import RiskMatrixTable from "@/components/RiskMatrixTable";
import CompareTopicCard from "@/components/CompareTopicCard";

const MAX_DOCS = 5;

export default function ComparePage() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [result, setResult] = useState<CompareResult | null>(null);
  const [totalTopics, setTotalTopics] = useState(0);
  const [comparing, setComparing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    listDocuments().then(setDocuments);
  }, []);

  useEffect(() => {
    if (!comparing) {
      setElapsed(0);
      return;
    }
    const start = Date.now();
    const timer = setInterval(() => setElapsed(Math.round((Date.now() - start) / 1000)), 1000);
    return () => clearInterval(timer);
  }, [comparing]);

  const elapsedLabel = `${Math.floor(elapsed / 60)}:${String(elapsed % 60).padStart(2, "0")}`;

  const toggle = useCallback((id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id],
    );
  }, []);

  async function handleCompare() {
    setComparing(true);
    setError(null);
    setResult(null);
    setTotalTopics(0);
    try {
      await streamCompare(selectedIds, undefined, {
        onMeta: (meta) => {
          setTotalTopics(Object.keys(meta.topic_labels).length);
          setResult({ ...meta, headline: "", topics: [], llm_error: null });
        },
        onTopic: (topic: CompareTopic) => {
          setResult((prev) => (prev ? { ...prev, topics: [...prev.topics, topic] } : prev));
        },
        onTopicError: (topic, message) => {
          setResult((prev) =>
            prev ? { ...prev, llm_error: `"${topic}" analiz edilemedi: ${message}` } : prev,
          );
        },
        onDone: (info) => {
          setResult((prev) => (prev ? { ...prev, headline: info.headline } : prev));
        },
        onError: (message) => setError(message),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Karşılaştırma başarısız oldu.");
    } finally {
      setComparing(false);
    }
  }

  const unanalyzed = result?.documents.filter((d) => d.risk_score === null) ?? [];
  const validTopics = result?.topics ?? [];

  return (
    <div className="flex flex-1 justify-center bg-paper">
      <main className="w-full max-w-3xl px-6 py-16 lg:max-w-4xl xl:max-w-5xl">
        <Link href="/" className="text-sm text-ink-3 hover:text-ink">
          ← Sözleşmeler
        </Link>
        <header className="mt-2 mb-6">
          <h1 className="text-3xl font-semibold tracking-tight text-ink">Sözleşme karşılaştırma</h1>
          <p className="mt-1 text-[15px] leading-relaxed text-ink-2">
            2 ile {MAX_DOCS} sözleşme seçin; fesih, sorumluluk, ödeme gibi konularda yan
            yana karşılaştırılsın.
          </p>
        </header>

        <DocumentPicker
          documents={documents}
          selected={selectedIds}
          onToggle={toggle}
          max={MAX_DOCS}
        />

        <button
          onClick={handleCompare}
          disabled={selectedIds.length < 2 || comparing}
          className="mt-4 rounded-md bg-accent px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-accent-hover hover:shadow-md disabled:opacity-40 disabled:shadow-none"
        >
          {comparing
            ? `Karşılaştırılıyor... (${elapsedLabel})`
            : `Karşılaştır${selectedIds.length > 0 ? ` (${selectedIds.length})` : ""}`}
        </button>

        {comparing && (
          <p className="mt-2 flex items-center gap-2 text-xs text-ink-3">
            <CompareSpinner />
            {totalTopics > 0
              ? `Konular tek tek karşılaştırılıyor: ${result?.topics.length ?? 0}/${totalTopics} tamamlandı.`
              : "Sözleşmeler hazırlanıyor…"}
          </p>
        )}

        {error && (
          <p
            className="mt-4 rounded-lg px-4 py-3 text-sm"
            style={{ backgroundColor: "var(--status-critical-bg)", color: "var(--status-critical)" }}
          >
            {error}
          </p>
        )}

        {result && (
          <div className="mt-8 space-y-6">
            {unanalyzed.length > 0 && (
              <p
                className="rounded-lg px-4 py-3 text-sm"
                style={{ backgroundColor: "var(--status-warning-bg)", color: "var(--status-warning)" }}
              >
                Şunlar henüz risk analizinden geçmedi, bu yüzden matriste eksik
                görünebilir: {unanalyzed.map((d) => d.title).join(", ")}.
              </p>
            )}
            {result.llm_error && (
              <p
                className="rounded-lg px-4 py-3 text-sm"
                style={{ backgroundColor: "var(--status-warning-bg)", color: "var(--status-warning)" }}
              >
                {result.llm_error}
              </p>
            )}
            {result.headline && (
              <p className="text-sm leading-relaxed text-ink-2">{result.headline}</p>
            )}

            <div>
              <h2 className="mb-3 text-sm font-medium text-ink-3">Risk matrisi</h2>
              <RiskMatrixTable documents={result.documents} rows={result.risk_matrix} />
            </div>

            {validTopics.length > 0 && (
              <div className="space-y-4">
                <h2 className="text-sm font-medium text-ink-3">Konu bazlı karşılaştırma</h2>
                {validTopics.map((topic) => (
                  <CompareTopicCard key={topic.topic} topic={topic} documents={result.documents} />
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

function CompareSpinner() {
  return (
    <svg className="h-3.5 w-3.5 animate-spin text-accent" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}
