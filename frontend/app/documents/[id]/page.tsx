"use client";

import { use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  ApiError,
  getAnalysis,
  getDocument,
  runAnalysis,
  type DocumentDetail,
  type RiskAnalysis,
} from "@/lib/api";
import RiskMeter from "@/components/RiskMeter";
import CategoryBarChart from "@/components/CategoryBarChart";
import FindingCard from "@/components/FindingCard";
import DocumentSummaryCard from "@/components/DocumentSummaryCard";
import ClauseList from "@/components/ClauseList";

export default function DocumentRiskPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  const [document, setDocument] = useState<DocumentDetail | null>(null);
  const [analysis, setAnalysis] = useState<RiskAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [notAnalyzed, setNotAnalyzed] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!analyzing) {
      setElapsed(0);
      return;
    }
    const start = Date.now();
    const timer = setInterval(() => setElapsed(Math.round((Date.now() - start) / 1000)), 1000);
    return () => clearInterval(timer);
  }, [analyzing]);

  const elapsedLabel = `${Math.floor(elapsed / 60)}:${String(elapsed % 60).padStart(2, "0")}`;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setNotAnalyzed(false);
    try {
      const doc = await getDocument(id);
      setDocument(doc);
      try {
        setAnalysis(await getAnalysis(id));
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          setNotAnalyzed(true);
        } else {
          throw err;
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Belge yüklenemedi.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleAnalyze() {
    setAnalyzing(true);
    setError(null);
    try {
      const result = await runAnalysis(id, { use_llm: true });
      setAnalysis(result);
      setNotAnalyzed(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Risk analizi başarısız oldu.");
    } finally {
      setAnalyzing(false);
    }
  }

  return (
    <div className="flex flex-1 justify-center bg-paper">
      <main className="w-full max-w-3xl px-6 py-16 lg:max-w-4xl xl:max-w-5xl">
        <Link href="/" className="text-sm text-ink-3 hover:text-ink">
          ← Sözleşmeler
        </Link>

        {loading ? (
          <p className="mt-6 text-sm text-ink-3">Yükleniyor...</p>
        ) : document ? (
          <>
            <header className="mt-4 mb-8 flex items-start justify-between gap-4">
              <div>
                <h1 className="text-3xl font-semibold tracking-tight text-ink">{document.title}</h1>
                <p className="mt-1 text-sm text-ink-3">
                  {document.filename} · {document.clause_count} madde
                  {document.doc_type ? ` · ${document.doc_type}` : ""}
                </p>
              </div>
              <Link
                href={`/chat?doc=${document.id}`}
                className="shrink-0 rounded-lg border border-border px-3 py-2 text-sm font-medium text-ink-2 hover:border-accent/50 hover:text-ink"
              >
                Sohbet
              </Link>
            </header>

            {error && (
              <p
                className="mb-4 rounded-lg px-4 py-3 text-sm"
                style={{ backgroundColor: "var(--status-critical-bg)", color: "var(--status-critical)" }}
              >
                {error}
              </p>
            )}

            <DocumentSummaryCard document={document} />

            {notAnalyzed && !analysis && (
              <div className="rounded-xl border border-dashed border-border px-6 py-10 text-center">
                {analyzing ? (
                  <div className="flex flex-col items-center gap-3">
                    <AnalyzingSpinner />
                    <p className="text-sm text-ink-2">Analiz ediliyor… ({elapsedLabel})</p>
                    <p className="text-xs text-ink-3">
                      Yerel model bu sözleşmeyi inceliyor, kalite için genellikle 1-2 dakika sürer.
                    </p>
                  </div>
                ) : (
                  <>
                    <p className="text-sm text-ink-2">Bu sözleşme için risk analizi henüz çalıştırılmadı.</p>
                    <button
                      onClick={handleAnalyze}
                      className="mt-4 rounded-md bg-accent px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-accent-hover hover:shadow-md"
                    >
                      Risk analizi yap
                    </button>
                  </>
                )}
              </div>
            )}

            {analysis && (
              <div className="space-y-6">
                {analysis.llm_error && (
                  <p
                    className="rounded-lg px-4 py-3 text-sm"
                    style={{ backgroundColor: "var(--status-warning-bg)", color: "var(--status-warning)" }}
                  >
                    {analysis.llm_error}
                  </p>
                )}

                <RiskMeter
                  score={analysis.risk_score}
                  severityCounts={analysis.severity_counts}
                  assessment={analysis.overall_assessment}
                />

                <CategoryBarChart categories={analysis.categories} />

                <div>
                  <div className="mb-3 flex items-center justify-between">
                    <h2 className="text-sm font-medium text-ink-3">
                      Bulgular ({analysis.findings.length})
                    </h2>
                    {analyzing ? (
                      <span className="flex items-center gap-2 text-sm text-ink-3">
                        <AnalyzingSpinner small />
                        Analiz ediliyor… ({elapsedLabel})
                      </span>
                    ) : (
                      <button onClick={handleAnalyze} className="text-sm text-ink-3 hover:text-ink">
                        Yeniden analiz et
                      </button>
                    )}
                  </div>
                  {analyzing && (
                    <p className="mb-3 text-xs text-ink-3">
                      Yerel model bu sözleşmeyi inceliyor, kalite için genellikle 1-2 dakika sürer.
                    </p>
                  )}
                  {analysis.findings.length === 0 ? (
                    <p className="text-sm text-ink-3">Herhangi bir risk bulgusu tespit edilmedi.</p>
                  ) : (
                    <ul className="space-y-2">
                      {analysis.findings.map((finding, i) => (
                        <FindingCard key={finding.rule_id ?? `${finding.category}-${i}`} finding={finding} />
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            )}

            <div className="mt-6">
              <ClauseList clauses={document.clauses} />
            </div>
          </>
        ) : (
          <p className="mt-6 text-sm" style={{ color: "var(--status-critical)" }}>
            {error}
          </p>
        )}
      </main>
    </div>
  );
}

function AnalyzingSpinner({ small = false }: { small?: boolean }) {
  const size = small ? "h-4 w-4" : "h-6 w-6";
  return (
    <svg className={`${size} animate-spin text-accent`} viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}
