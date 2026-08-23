"use client";

import type { DocumentSummary } from "@/lib/api";

type Props = {
  documents: DocumentSummary[];
  selected: string[];
  onToggle: (id: string) => void;
  max: number;
};

export default function DocumentPicker({ documents, selected, onToggle, max }: Props) {
  if (documents.length === 0) return null;

  return (
    <ul className="card divide-y divide-border overflow-hidden rounded-lg">
      {documents.map((doc) => {
        const checked = selected.includes(doc.id);
        const disabled = !checked && selected.length >= max;
        return (
          <li key={doc.id}>
            <label
              className={`flex items-center gap-3 bg-surface px-4 py-3 ${
                disabled ? "opacity-40" : "cursor-pointer hover:bg-paper"
              }`}
            >
              <input
                type="checkbox"
                checked={checked}
                disabled={disabled}
                onChange={() => onToggle(doc.id)}
                className="h-4 w-4 shrink-0 rounded border-border accent-accent"
              />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-ink">{doc.title}</p>
                <p className="text-xs text-ink-3">{doc.doc_type ?? "Tür belirsiz"}</p>
              </div>
              <span className="shrink-0 text-xs text-ink-3">
                {doc.risk_score === null
                  ? "Analiz edilmedi"
                  : `Risk: ${Math.round(doc.risk_score)}`}
              </span>
            </label>
          </li>
        );
      })}
    </ul>
  );
}
