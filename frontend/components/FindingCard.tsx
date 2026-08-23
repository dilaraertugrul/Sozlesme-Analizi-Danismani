"use client";

import { useState } from "react";
import type { Finding } from "@/lib/api";
import SeverityBadge from "@/components/SeverityBadge";

const IMPACT_LABEL: Record<string, string> = {
  koruyucu: "Koruyucu",
  dengeli: "Dengeli",
  agresif: "Agresif",
};

export default function FindingCard({ finding }: { finding: Finding }) {
  const [open, setOpen] = useState(false);

  return (
    <li className="card rounded-lg">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-start justify-between gap-3 px-4 py-3 text-left"
      >
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <SeverityBadge severity={finding.severity} />
            <span className="text-xs text-ink-3">
              {finding.category_label}
              {finding.clause_ref ? ` · ${finding.clause_ref}` : ""}
            </span>
          </div>
          <p className="mt-1.5 font-medium text-ink">{finding.title}</p>
        </div>
        <svg
          className={`mt-1 h-4 w-4 shrink-0 text-ink-3 transition-transform ${open ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={2}
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
        </svg>
      </button>

      {open && (
        <div className="space-y-3 border-t border-border px-4 py-3 text-sm">
          {finding.excerpt && (
            <blockquote className="border-l-2 border-border pl-3 text-ink-2 italic">
              &ldquo;{finding.excerpt}&rdquo;
            </blockquote>
          )}
          <p className="text-ink-2">
            <span className="font-medium text-ink">Neden risk taşır: </span>
            {finding.rationale}
          </p>
          <p className="text-ink-2">
            <span className="font-medium text-ink">Öneri: </span>
            {finding.recommendation}
          </p>

          {finding.options.length > 0 && (
            <div>
              <p className="font-medium text-ink">Müzakere seçenekleri</p>
              <ul className="mt-1.5 space-y-1.5">
                {finding.options.map((option, i) => (
                  <li key={i} className="rounded-md bg-paper px-3 py-2 text-ink-2">
                    <span className="font-medium text-ink">{option.label}</span>{" "}
                    <span className="text-xs text-ink-3">
                      ({IMPACT_LABEL[option.impact] ?? option.impact})
                    </span>
                    <p className="mt-0.5">{option.detail}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {finding.source === "llm" && (
            <p className="text-xs text-ink-3">Ek inceleme sırasında tespit edildi.</p>
          )}
        </div>
      )}
    </li>
  );
}
