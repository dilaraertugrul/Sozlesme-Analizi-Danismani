"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  compareDocuments,
  listDocuments,
  type CompareResult,
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
  const [comparing, setComparing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listDocuments().then(setDocuments);
  }, []);

  const toggle = useCallback((id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id],
    );
  }, []);

  async function handleCompare() {
    setComparing(true);
    setError(null);
    setResult(null);
    try {
      setResult(await compareDocuments(selectedIds));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Karşılaştırma başarısız oldu.");
    } finally {
      setComparing(false);
    }
  }

  const unanalyzed = result?.documents.filter((d) => d.risk_score === null) ?? [];

  // Küçük yerel modeller ara sıra "topic" alanına yanlışlıkla bir belge id'si
  // yazıyor (beklenen konu adı yerine) — bu bozuk kartları göstermeyelim.
  const docIds = new Set(result?.documents.map((d) => d.id) ?? []);
  const validTopics = result?.topics.filter((t) => !docIds.has(t.topic)) ?? [];

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
            ? "Karşılaştırılıyor..."
            : `Karşılaştır${selectedIds.length > 0 ? ` (${selectedIds.length})` : ""}`}
        </button>

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
