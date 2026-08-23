"use client";

import { useState } from "react";
import Link from "next/link";
import type { DocumentSummary } from "@/lib/api";

type Props = {
  documents: DocumentSummary[];
  onDelete: (id: string) => Promise<void>;
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("tr-TR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export default function DocumentList({ documents, onDelete }: Props) {
  const [deletingId, setDeletingId] = useState<string | null>(null);

  if (documents.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-border px-4 py-8 text-center text-sm text-ink-3">
        Henüz yüklenmiş bir sözleşme yok.
      </p>
    );
  }

  async function handleDelete(id: string) {
    setDeletingId(id);
    try {
      await onDelete(id);
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <ul className="grid grid-cols-1 gap-3 lg:grid-cols-2">
      {documents.map((doc) => (
        <li
          key={doc.id}
          className="card card-interactive group flex items-center justify-between gap-4 rounded-xl border-l-4 px-4 py-3.5"
          style={{ borderLeftColor: doc.analyzed ? "var(--secondary)" : "var(--gold)" }}
        >
          <div className="min-w-0">
            <Link
              href={`/documents/${doc.id}`}
              className="block truncate font-medium text-ink group-hover:text-accent"
            >
              {doc.title}
            </Link>
            <p className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-ink-3">
              <span>{doc.filename}</span>
              {doc.doc_type && (
                <>
                  <span aria-hidden>·</span>
                  <span>{doc.doc_type}</span>
                </>
              )}
              <span aria-hidden>·</span>
              <span>{doc.clause_count} madde</span>
              <span aria-hidden>·</span>
              <span>{formatDate(doc.created_at)}</span>
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-3">
            <Link
              href={`/documents/${doc.id}`}
              className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold"
              style={{
                backgroundColor: doc.analyzed ? "var(--badge-success-bg)" : "var(--badge-pending-bg)",
                color: doc.analyzed ? "var(--badge-success-text)" : "var(--badge-pending-text)",
              }}
            >
              <span
                className="h-1.5 w-1.5 shrink-0 rounded-full"
                style={{
                  backgroundColor: doc.analyzed ? "var(--badge-success-text)" : "var(--badge-pending-text)",
                }}
                aria-hidden
              />
              {doc.analyzed ? "Analiz edildi" : "Analiz bekliyor"}
            </Link>
            <button
              onClick={() => handleDelete(doc.id)}
              disabled={deletingId === doc.id}
              className="rounded-md p-1.5 text-ink-3 transition-colors hover:bg-[var(--status-critical-bg)] hover:text-[var(--status-critical)] disabled:opacity-50"
              aria-label={`${doc.title} belgesini sil`}
            >
              <svg
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"
                />
              </svg>
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}
