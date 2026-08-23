"use client";

import { useState } from "react";
import type { DocumentClause } from "@/lib/api";

export default function ClauseList({ clauses }: { clauses: DocumentClause[] }) {
  const [open, setOpen] = useState(false);

  if (clauses.length === 0) return null;

  return (
    <div className="card">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between px-5 py-3.5 text-left"
      >
        <span className="text-sm font-medium text-ink-2">
          Sözleşme metni ({clauses.length} madde)
        </span>
        <svg
          className={`h-4 w-4 shrink-0 text-ink-3 transition-transform ${open ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={2}
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
        </svg>
      </button>

      {open && (
        <div className="max-h-[600px] space-y-4 overflow-y-auto border-t border-border px-5 py-4">
          {clauses.map((clause) => (
            <div key={clause.id}>
              <p className="text-xs font-medium text-ink-3">
                {clause.label}
                {clause.page ? ` · Sayfa ${clause.page}` : ""}
              </p>
              <p className="mt-0.5 whitespace-pre-wrap text-sm text-ink-2">{clause.text}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
